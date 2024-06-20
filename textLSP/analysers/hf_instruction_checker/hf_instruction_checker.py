import logging

from typing import Optional, List
from pygls.server import LanguageServer
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
        MessageType,
)

from ..hf_checker import HFCheckerAnalyser
from ...types import ProgressBar, Interval


logger = logging.getLogger(__name__)


class HFInstructionCheckerAnalyser(HFCheckerAnalyser):
    CONFIGURATION_INSTRUCTION = 'instruction'
    CONFIGURATION_PROMPT_MAGIC = 'prompt_magic'

    SETTINGS_DEFAULT_INSTRUCTION = 'Fix the grammar:'
    SETTINGS_DEFAULT_PROMPT_MAGIC = '%HF% '

    def __init__(self, language_server: LanguageServer, config: dict, name: str):
        super().__init__(language_server, config, name)

        instruction = self.config.get(self.CONFIGURATION_INSTRUCTION, self.SETTINGS_DEFAULT_INSTRUCTION)
        if instruction is None:
            self.config[self.CONFIGURATION_INSTRUCTION] = ''

    def corrector(self, text):
        instruction = self.config.get(self.CONFIGURATION_INSTRUCTION, self.SETTINGS_DEFAULT_INSTRUCTION)
        inp = f'{instruction} {text}' if len(instruction) > 0 else text

        return self._corrector(inp)

    def get_completions(self, params: Optional[CompletionParams] = None) -> Optional[CompletionList]:
        if params.position == Position(line=0, character=0):
            return None

        doc = self.get_document(params)
        line = doc.lines[params.position.line]
        magic = self.config.get(self.CONFIGURATION_PROMPT_MAGIC, self.SETTINGS_DEFAULT_PROMPT_MAGIC)

        line_prefix = line[:params.position.character].strip()
        if len(line_prefix) == 0 or line_prefix in magic:
            return [
                CompletionItem(
                    label=magic,
                    detail='hf_instruction_checker magic command for text'
                    ' generation based on the prompt that follows.'
                )
            ]

    def command_generate(
            self,
            uri: str,
            interval: str,
    ):
        with ProgressBar(
                self.language_server,
                f'{self.name} generating',
                token=self._progressbar_token
        ):
            magic = self.config.get(self.CONFIGURATION_PROMPT_MAGIC, self.SETTINGS_DEFAULT_PROMPT_MAGIC)
            doc = self.get_document(uri)
            interval = Interval(**eval(interval))
            range = doc.range_at_offset(interval.start, interval.length, False)
            lines = doc.lines[range.start.line:range.end.line+1]
            lines[0] = lines[0][lines[0].find(magic)+len(magic):]
            prompt = '\n'.join(lines)

            new_text = self._corrector(prompt)
            if len(new_text) == 0:
                return
            new_text = new_text.pop(0)['generated_text']
            new_text += '\n'

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

        if len(doc.lines) > 0:
            line = doc.lines[params.range.start.line].strip()
        else:
            line = ''
        magic = self.config.get(self.CONFIGURATION_PROMPT_MAGIC, self.SETTINGS_DEFAULT_PROMPT_MAGIC)
        if magic in line:
            if res is None:
                res = list()

            start_offset = doc.offset_at_position(params.range.start)
            end_offset = doc.offset_at_position(params.range.end)
            paragraphs = doc.paragraphs_at_offset(
                start_offset,
                min_offset=end_offset,
                cleaned=False
            )
            
            if doc.position_at_offset(paragraphs[0].start, False).line != params.range.start.line:
                # only if prompt is the first line of the paragraph
                return res

            start_offset = paragraphs[0].start
            end_offset = paragraphs[-1].start+paragraphs[-1].length
            interval = Interval(start_offset, end_offset)
            interval = str({
                'start': start_offset,
                'length': end_offset-start_offset+1,
            })
            title = 'Prompt HF'
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
                            'interval': interval,
                        }],
                    ),
                )
            )

        return res
