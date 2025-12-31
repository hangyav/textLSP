import logging
from typing import List, Optional, Tuple

import ollama
from lsprotocol.types import (
    ApplyWorkspaceEditParams,
    CodeAction,
    CodeActionParams,
    Command,
    CompletionItem,
    CompletionList,
    CompletionParams,
    Diagnostic,
    MessageType,
    Position,
    Range,
    ShowMessageParams,
    TextDocumentEdit,
    TextEdit,
    VersionedTextDocumentIdentifier,
    WorkspaceEdit,
)
from pygls.lsp.server import LanguageServer

from ...documents.document import BaseDocument
from ...types import ConfigurationError, Interval, ProgressBar, TokenDiff
from ..analyser import Analyser

logger = logging.getLogger(__name__)


class OllamaAnalyser(Analyser):
    CONFIGURATION_MODEL = "model"
    CONFIGURATION_KEEP_ALIVE = "keep_alive"
    CONFIGURATION_EDIT_INSTRUCTION = "edit_instruction"
    CONFIGURATION_TEMPERATURE = "temperature"
    CONFIGURATION_MAX_TOKEN = "max_token"
    CONFIGURATION_PROMPT_MAGIC = "prompt_magic"

    SETTINGS_DEFAULT_MODEL = "gemma3:4b"
    SETTINGS_DEFAULT_KEEP_ALIVE = "10m"
    SETTINGS_DEFAULT_EDIT_INSTRUCTION = (
        "Correct all grammar mistakes in the following text."
        " Be rigorous but do not change the meaning and style, or add or remove content."
        " Output only the corrected text even if it is correct."
    )
    SETTINGS_DEFAULT_TEMPERATURE = 0
    SETTINGS_DEFAULT_MAX_TOKEN = 50
    SETTINGS_DEFAULT_PROMPT_MAGIC = "%OLLAMA% "
    SETTINGS_DEFAULT_CHECK_ON = {
        Analyser.CONFIGURATION_CHECK_ON_OPEN: False,
        Analyser.CONFIGURATION_CHECK_ON_CHANGE: False,
        Analyser.CONFIGURATION_CHECK_ON_SAVE: True,
    }

    def __init__(self, language_server: LanguageServer, config: dict, name: str):
        super().__init__(language_server, config, name)

        try:
            # test if the server is running
            ollama.list()
        except ConnectionError:
            raise ConfigurationError(
                "Ollama server is not running. Start it manually and restart textLSP."
                "To install Ollama see: https://ollama.com/download"
            )

        try:
            # test if the model is available
            ollama.show(
                self.config.get(self.CONFIGURATION_MODEL, self.SETTINGS_DEFAULT_MODEL),
            )
        except ollama.ResponseError:
            try:
                with ProgressBar(
                    self.language_server,
                    f"{self.name} downloading {self.config.get(self.CONFIGURATION_MODEL, self.SETTINGS_DEFAULT_MODEL)}",
                    token=self._progressbar_token,
                ):
                    ollama.pull(
                        self.config.get(
                            self.CONFIGURATION_MODEL, self.SETTINGS_DEFAULT_MODEL
                        )
                    )
            except Exception as e:
                logger.exception(e, stack_info=True)
                raise ConfigurationError(f"{self.name}: {e}")

    def _generate(self, prompt, options=None, keep_alive=None):
        logger.debug(f"Generating for input: {prompt}")
        if options is None:
            options = {
                "seed": 42,
                "temperature": self.config.get(
                    self.CONFIGURATION_TEMPERATURE, self.SETTINGS_DEFAULT_TEMPERATURE
                ),
            }
        if keep_alive is None:
            keep_alive = self.config.get(
                self.CONFIGURATION_KEEP_ALIVE, self.SETTINGS_DEFAULT_KEEP_ALIVE
            )
        try:
            res = ollama.chat(
                model=self.config.get(
                    self.CONFIGURATION_MODEL, self.SETTINGS_DEFAULT_MODEL
                ),
                messages=[{"role": "user", "content": prompt}],
                options=options,
                keep_alive=keep_alive,
            )
            logger.debug(f"Generation output: {res}")
        except ollama.ResponseError as e:
            self.language_server.window_show_message(
                ShowMessageParams(
                    message=str(e),
                    type=MessageType.Error,
                )
            )
            return None

        return res

    def _analyse(
        self, text, doc, offset=0
    ) -> Tuple[List[Diagnostic], List[CodeAction]]:
        diagnostics = list()
        code_actions = list()

        # we don not want trailing whitespace
        text = text.rstrip()

        res = self._generate(
            prompt=f"{self.config.get(self.CONFIGURATION_EDIT_INSTRUCTION, self.SETTINGS_DEFAULT_EDIT_INSTRUCTION)}{text}",
        )
        if res is None:
            return [], []

        edits = TokenDiff.token_level_diff(text, res['message']['content'].strip())

        for edit in edits:
            if edit.type == TokenDiff.INSERT:
                if edit.offset >= len(text):
                    edit.new_token = f" {edit.new_token}"
                else:
                    edit.new_token = f" {edit.new_token} "
                    edit.old_token = " "
                    edit.offset -= 1
                    edit.length += 1

            token = edit.old_token

            range = doc.range_at_offset(edit.offset + offset, edit.length, True)
            range = Range(
                start=range.start,
                end=Position(
                    line=range.end.line,
                    character=range.end.character + 1,
                ),
            )

            if edit.type == TokenDiff.INSERT:
                message = f'insert "{edit.new_token}"'
            elif edit.type == TokenDiff.REPLACE:
                message = f'"{token}": use "{edit.new_token}" instead'
            else:
                message = f'"{token}": remove'

            diagnostic = Diagnostic(
                range=range,
                message=message,
                source="ollama",
                severity=self.get_severity(),
                code=f"ollama:{edit.type}",
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
        for paragraph in doc.paragraphs_at_offset(
            0, len(doc.cleaned_source), cleaned=True
        ):
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
            for paragraph in doc.paragraphs_at_offset(
                change.start,
                min_offset=change.start + change.length - 1,
                cleaned=True,
            ):
                if paragraph in checked:
                    continue

                diags, actions = self._handle_paragraph(doc, paragraph)
                diagnostics.extend(diags)
                code_actions.extend(actions)
                checked.add(paragraph)

        self.add_diagnostics(doc, diagnostics)
        self.add_code_actions(doc, code_actions)

    def _handle_paragraph(self, doc: BaseDocument, paragraph: Interval):
        if (
            len(doc.text_at_offset(paragraph.start, paragraph.length, True).strip())
            == 0
        ):
            return [], []

        pos_range = doc.range_at_offset(paragraph.start, paragraph.length, True)
        self.remove_code_items_at_range(doc, pos_range)

        diags, actions = self._analyse(
            doc.text_at_offset(paragraph.start, paragraph.length, True),
            doc,
            paragraph.start,
        )

        diagnostics = [diag for diag in diags if diag.range.start >= pos_range.start]
        code_actions = [
            action
            for action in actions
            if action.edit.document_changes[0].edits[0].range.start >= pos_range.start
        ]

        return diagnostics, code_actions

    def command_generate(self, uri: str, prompt: str, position: str, new_line=True):
        with ProgressBar(
            self.language_server,
            f"{self.name} generating",
            token=self._progressbar_token,
        ):
            doc = self.get_document(uri)

            result = self._generate(prompt)
            if result is None:
                return [], []

            new_text = f"{result['message']['content'].strip()}\n"
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
                        ],
                    )
                ]
            )
            self.language_server.workspace_apply_edit(
                ApplyWorkspaceEditParams(edit, "textlsp.ollama.generate")
            )

    def get_code_actions(self, params: CodeActionParams) -> Optional[List[CodeAction]]:
        doc = self.get_document(params)
        res = super().get_code_actions(params)

        if len(doc.lines) > 0:
            line = doc.lines[params.range.start.line].strip()
        else:
            line = ""
        magic = self.config.get(
            self.CONFIGURATION_PROMPT_MAGIC, self.SETTINGS_DEFAULT_PROMPT_MAGIC
        )
        if magic in line:
            if res is None:
                res = list()

            paragraph = doc.paragraph_at_position(params.range.start, False)
            position = doc.position_at_offset(paragraph.start + paragraph.length, False)
            position = str({"line": position.line, "character": position.character})
            prompt = doc.text_at_offset(paragraph.start, paragraph.length, False)
            prompt = prompt[prompt.find(magic) + len(magic) :]
            title = "Prompt Ollama"
            res.append(
                self.build_command_action(
                    doc=doc,
                    title=title,
                    command=Command(
                        title=title,
                        command=self.language_server.COMMAND_CUSTOM,
                        arguments=[
                            {
                                "command": "generate",
                                "analyser": self.name,
                                "uri": doc.uri,
                                "prompt": prompt,
                                "position": position,
                                "new_line": True,
                            }
                        ],
                    ),
                )
            )

        return res

    def get_completions(
        self, params: Optional[CompletionParams] = None
    ) -> Optional[CompletionList]:
        if params.position == Position(line=0, character=0):
            return None

        doc = self.get_document(params)
        line = doc.lines[params.position.line]
        magic = self.config.get(
            self.CONFIGURATION_PROMPT_MAGIC, self.SETTINGS_DEFAULT_PROMPT_MAGIC
        )

        line_prefix = line[: params.position.character].strip()
        if len(line_prefix) == 0 or line_prefix in magic:
            return [
                CompletionItem(
                    label=magic,
                    detail="Ollama magic command for text generation based on"
                    " the prompt that follows.",
                )
            ]
