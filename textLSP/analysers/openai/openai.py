import logging
import openai

from typing import List, Tuple, Optional
from lsprotocol.types import (
        Diagnostic,
        Range,
        Position,
        TextEdit,
        CodeAction,
        WorkspaceEdit,
        Command,
        CodeActionParams,
        TextDocumentEdit,
        VersionedTextDocumentIdentifier,
        CompletionParams,
        CompletionList,
        CompletionItem,
)
from pygls.server import LanguageServer

from ..analyser import Analyser
from ...types import Interval, ConfigurationError, TokenDiff
from ...documents.document import BaseDocument


logger = logging.getLogger(__name__)


class OpenAIAnalyser(Analyser):
    CONFIGURATION_API_KEY = 'api_key'
    CONFIGURATION_EDIT_MODEL = 'edit_model'
    CONFIGURATION_MODEL = 'model'
    CONFIGURATION_EDIT_INSTRUCTION = 'edit_instruction'
    CONFIGURATION_TEMPERATURE = 'temperature'
    CONFIGURATION_MAX_TOKEN = 'max_token'
    CONFIGURATION_PROMPT_MAGIC = 'prompt_magic'

    SETTINGS_DEFAULT_EDIT_MODEL = 'text-davinci-edit-001'
    SETTINGS_DEFAULT_MODEL = 'text-babbage-001'
    SETTINGS_DEFAULT_EDIT_INSTRUCTION = 'Fix the spelling and grammar errors'
    SETTINGS_DEFAULT_TEMPERATURE = 0
    SETTINGS_DEFAULT_MAX_TOKEN = 16
    SETTINGS_DEFAULT_PROMPT_MAGIC = '%OPENAI% '
    SETTINGS_DEFAULT_CHECK_ON = {
        Analyser.CONFIGURATION_CHECK_ON_OPEN: False,
        Analyser.CONFIGURATION_CHECK_ON_CHANGE: False,
        Analyser.CONFIGURATION_CHECK_ON_SAVE: False,
    }

    def __init__(self, language_server: LanguageServer, config: dict, name: str):
        super().__init__(language_server, config, name)
        if self.CONFIGURATION_API_KEY not in self.config:
            raise ConfigurationError(f'Reqired parameter: {name}.{self.CONFIGURATION_API_KEY}')
        openai.api_key = self.config[self.CONFIGURATION_API_KEY]

    def _edit(self, text) -> List[TokenDiff]:
        res = openai.Edit.create(
            model=self.config.get(self.CONFIGURATION_EDIT_MODEL, self.SETTINGS_DEFAULT_EDIT_MODEL),
            instruction=self.config.get(self.CONFIGURATION_EDIT_INSTRUCTION, self.SETTINGS_DEFAULT_EDIT_INSTRUCTION),
            input=text,
            temperature=self.config.get(self.CONFIGURATION_TEMPERATURE, self.SETTINGS_DEFAULT_TEMPERATURE),
        )
        if len(res.choices) > 0:
            return TokenDiff.token_level_diff(text, res.choices[0]['text'].strip())
        return []

    def _generate(self, text) -> Optional[str]:
        res = openai.Completion.create(
            model=self.config.get(self.CONFIGURATION_MODEL, self.SETTINGS_DEFAULT_MODEL),
            prompt=text,
            temperature=self.config.get(self.CONFIGURATION_TEMPERATURE, self.SETTINGS_DEFAULT_TEMPERATURE),
            max_tokens=self.config.get(self.CONFIGURATION_MAX_TOKEN, self.SETTINGS_DEFAULT_MAX_TOKEN),
        )

        if len(res.choices) > 0:
            return res.choices[0]['text'].strip()

        return None

    def _analyse(self, text, doc, offset=0) -> Tuple[List[Diagnostic], List[CodeAction]]:
        diagnostics = list()
        code_actions = list()

        for edit in self._edit(text):
            if edit.type == TokenDiff.INSERT:
                if edit.offset >= len(text):
                    edit.new_token = f' {edit.new_token}'
                else:
                    edit.new_token = f' {edit.new_token} '
                    edit.old_token = ' '
                    edit.offset -= 1
                    edit.length += 1

            token = edit.old_token

            range = doc.range_at_offset(edit.offset+offset, edit.length, True)
            range = Range(
                start=range.start,
                end=Position(
                    line=range.end.line,
                    character=range.end.character+1,
                )
            )

            diagnostic = Diagnostic(
                range=range,
                message=f'"{token}": openai {edit.type}',
                source='openai',
                severity=self.get_severity(),
            )
            action = self.build_single_suggestion_action(
                doc=doc,
                title=f'"{token}" -> "{edit.new_token}"',
                edit=TextEdit(
                    range=diagnostic.range,
                    new_text=edit.new_token,
                ),
                diagnostic=diagnostic,
            )
            code_actions.append(action)
            diagnostics.append(diagnostic)

        return diagnostics, code_actions

    def _did_open(self, doc: BaseDocument):
        diagnostics = list()
        code_actions = list()
        checked = set()
        for paragraph in doc.paragraphs_at_offset(0, len(doc.cleaned_source), True):
            diags, actions = self._handle_paragraph(doc, paragraph)
            diagnostics.extend(diags)
            code_actions.extend(actions)
            checked.add(paragraph)

        self.add_diagnostics(doc, diagnostics)
        self.add_code_actions(doc, code_actions)

    def _did_change(self, doc: BaseDocument, changes: List[Interval]):
        diagnostics = list()
        code_actions = list()
        checked = set()
        for change in changes:
            paragraph = doc.paragraph_at_offset(
                change.start,
                min_length=change.length,
                cleaned=True,
            )
            if paragraph in checked:
                continue

            diags, actions = self._handle_paragraph(doc, paragraph)
            diagnostics.extend(diags)
            code_actions.extend(actions)
            checked.add(paragraph)

        self.add_diagnostics(doc, diagnostics)
        self.add_code_actions(doc, code_actions)

    def _handle_paragraph(self, doc: BaseDocument, paragraph: Interval):
        if len(doc.text_at_offset(paragraph.start, paragraph.length, True).strip()) == 0:
            return [], []

        pos_range = doc.range_at_offset(
            paragraph.start,
            paragraph.length,
            True
        )
        self.remove_code_items_at_rage(doc, pos_range)

        diags, actions = self._analyse(
            doc.text_at_offset(
                paragraph.start,
                paragraph.length,
                True
            ),
            doc,
            paragraph.start,
        )

        diagnostics = [
            diag
            for diag in diags
            if diag.range.start >= pos_range.start
        ]
        code_actions = [
            action
            for action in actions
            if action.edit.document_changes[0].edits[0].range.start >= pos_range.start
        ]

        return diagnostics, code_actions

    def command_generate(
            self,
            uri: str,
            prompt: str,
            position: str,
            new_line=True
    ):
        doc = self.get_document(uri)

        new_text = self._generate(prompt)
        new_text += '\n'
        position = Position(**eval(position))
        range = Range(
            start=position,
            end=position,
        )

        edit = WorkspaceEdit(
            document_changes=[
                TextDocumentEdit(
                    text_document=VersionedTextDocumentIdentifier(
                        uri=doc.uri,
                        version=doc.version,
                    ),
                    edits=[
                        TextEdit(
                            range=range,
                            new_text=new_text,
                        ),

                    ]
                )
            ]
        )
        self.language_server.apply_edit(edit, 'textlsp.openai.generate')

    def get_code_actions(self, params: CodeActionParams) -> Optional[List[CodeAction]]:
        doc = self.get_document(params)
        res = super().get_code_actions(params)

        if params.range.start != params.range.end:
            return res

        line = doc.lines[params.range.start.line].strip()
        magic = self.config.get(self.CONFIGURATION_PROMPT_MAGIC, self.SETTINGS_DEFAULT_PROMPT_MAGIC)
        if magic in line:
            if res is None:
                res = list()

            paragraph = doc.paragraph_at_position(params.range.start, False)
            position = doc.position_at_offset(paragraph.start+paragraph.length, False)
            position = str({'line': position.line, 'character': position.character})
            prompt = doc.text_at_offset(paragraph.start, paragraph.length, False)
            prompt = prompt[prompt.find(magic)+len(magic):]
            title = 'Prompt OpenAI'
            res.append(
                self.build_command_action(
                    doc=doc,
                    title=title,
                    command=Command(
                        title=title,
                        command=self.language_server.COMMAND_CUSTOM,
                        arguments=[{
                            'command': 'generate',
                            'analyser': self.name,
                            'uri': doc.uri,
                            'prompt': prompt,
                            'position': position,
                            'new_line': True
                        }],
                    ),
                )
            )

        return res

    def get_completions(self, params: Optional[CompletionParams] = None) -> Optional[CompletionList]:
        if params.position == Position(line=0, character=0):
            return None

        doc = self.get_document(params)
        line = doc.lines[params.position.line]
        magic = self.config.get(self.CONFIGURATION_PROMPT_MAGIC, self.SETTINGS_DEFAULT_PROMPT_MAGIC)

        if len(line[:params.position.character].strip()) == 0:
            return [
                CompletionItem(
                    label=magic,
                    detail='OpenAI magic command for text generation based on'
                    ' the prompt that follows.'
                )
            ]
