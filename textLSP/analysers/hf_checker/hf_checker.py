import logging

from re import Match
from itertools import chain
from typing import List, Tuple
from lsprotocol.types import (
        Diagnostic,
        Range,
        Position,
        TextEdit,
        CodeAction,
        MessageType,
)
from pygls.server import LanguageServer
from transformers import pipeline

from ..analyser import Analyser
from ...types import (
    Interval,
    LINE_PATTERN,
    TokenDiff,
)
from ...documents.document import BaseDocument
from ...nn_utils import get_device


logger = logging.getLogger(__name__)


class HFCheckerAnalyser(Analyser):
    CONFIGURATION_GPU = 'gpu'
    CONFIGURATION_MODEL = 'model'
    CONFIGURATION_MIN_LENGTH = 'min_length'
    CONFIGURATION_INSTRUCITON = 'instruction'

    SETTINGS_DEFAULT_GPU = False
    SETTINGS_DEFAULT_MODEL = 'grammarly/coedit-large'
    SETTINGS_DEFAULT_MIN_LENGTH = 0
    SETTINGS_DEFAULT_INSTRUCTION = 'Fix the grammar:'

    INSTRUCTION_MODELS = {
        'grammarly/coedit-large',
        'grammarly/coedit-xl',
        'grammarly/coedit-xl-composite',
        'grammarly/coedit-xxl',
        'jbochi/coedit-base',
        'jbochi/coedit-small',
        'jbochi/candle-coedit-quantized',
    }

    NON_INSTRUCTION_MODELS = {
        'pszemraj/grammar-synthesis-small',
        'pszemraj/grammar-synthesis-large',
        'pszemraj/flan-t5-large-grammar-synthesis',
        'pszemraj/flan-t5-xl-grammar-synthesis',
        'pszemraj/bart-base-grammar-synthesis',
    }

    def __init__(self, language_server: LanguageServer, config: dict, name: str):
        super().__init__(language_server, config, name)
        use_gpu = self.config.get(self.CONFIGURATION_GPU, self.SETTINGS_DEFAULT_GPU)

        instruction = self.config.get(self.CONFIGURATION_INSTRUCITON, self.SETTINGS_DEFAULT_INSTRUCTION)
        if instruction is None:
            self.config[self.CONFIGURATION_INSTRUCITON] = ''
            instruction = ''
        model = self.config.get(self.CONFIGURATION_MODEL, self.SETTINGS_DEFAULT_MODEL)
        if len(instruction) > 0 and model in self.NON_INSTRUCTION_MODELS:
            language_server.show_message(
                f'Model {model} does not support instructions. Known instruction'
                f' models: {", ".join(self.INSTRUCTION_MODELS)}',
                MessageType.Error,
            )
            self.config[self.CONFIGURATION_INSTRUCITON] = ''
        elif len(instruction) == 0 and model in self.INSTRUCTION_MODELS:
            language_server.show_message(
                f'Model {model} requires an instruction. Using default. Known'
                f' non-instruction models:'
                f' {", ".join(self.NON_INSTRUCTION_MODELS)}',
                MessageType.Error,
            )
            self.config[self.CONFIGURATION_INSTRUCITON] = self.SETTINGS_DEFAULT_INSTRUCTION

        self.corrector = pipeline(
            'text2text-generation',
            model,
            device=get_device(use_gpu),
        )

    def _analyse_lines(self, text, doc, offset=0) -> Tuple[List[Diagnostic], List[CodeAction]]:
        diagnostics = list()
        code_actions = list()

        sidx = 0
        for match in chain(LINE_PATTERN.finditer(text), [len(text)]):
            if type(match) == Match:
                eidx = match.end()
            else:
                eidx = match
            if sidx == eidx:
                continue

            line = text[sidx:eidx]
            diags, actions = self._analyse(line, doc, sidx+offset)
            diagnostics.extend(diags)
            code_actions.extend(actions)

            sidx = eidx

        return diagnostics, code_actions

    def _analyse(self, text, doc, offset=0) -> Tuple[List[Diagnostic], List[CodeAction]]:
        text = text.strip()
        if len(text) < self.config.get(self.CONFIGURATION_MIN_LENGTH, self.SETTINGS_DEFAULT_MIN_LENGTH):
            return [], []

        instruction = self.config.get(self.CONFIGURATION_INSTRUCITON, self.SETTINGS_DEFAULT_INSTRUCTION)
        inp = f'{instruction} {text}' if len(instruction) > 0 else text

        diagnostics = list()
        code_actions = list()

        corrected = self.corrector(inp)
        if len(corrected) == 0:
            return [], []
        corrected = corrected.pop(0)['generated_text']

        edits = TokenDiff.token_level_diff(text, corrected.strip())
        for edit in edits:
            if edit.type == TokenDiff.INSERT:
                if edit.offset >= len(text):
                    edit.new_token = f' {edit.new_token}'
                else:
                    edit.new_token = f' {edit.new_token} '
                    edit.old_token = ' '
                    edit.offset -= 1
                    edit.length += 1

            token = edit.old_token

            if edit.offset+offset >= len(doc.cleaned_source):
                edit.offset -= 1
            range = doc.range_at_offset(edit.offset+offset, edit.length, True)
            range = Range(
                start=range.start,
                end=Position(
                    line=range.end.line,
                    character=range.end.character+1,
                )
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
                source='hf_checker',
                severity=self.get_severity(),
                code=f'hf_checker:{edit.type}',
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
        diagnostics, actions = self._analyse_lines(doc.cleaned_source, doc)
        self.add_diagnostics(doc, diagnostics)
        self.add_code_actions(doc, actions)

    def _did_change(self, doc: BaseDocument, changes: List[Interval]):
        diagnostics = list()
        code_actions = list()
        checked = set()
        for change in changes:
            paragraph = doc.paragraph_at_offset(
                change.start,
                min_offset=change.start + change.length-1,
                cleaned=True,
            )
            if paragraph in checked:
                continue

            pos_range = doc.range_at_offset(
                paragraph.start,
                paragraph.length,
                True
            )
            self.remove_code_items_at_range(doc, pos_range)

            diags, actions = self._analyse_lines(
                doc.text_at_offset(
                    paragraph.start,
                    paragraph.length,
                    True
                ),
                doc,
                paragraph.start,
            )

            diagnostics.extend([
                diag
                for diag in diags
                if diag.range.start >= pos_range.start
            ])
            code_actions.extend([
                action
                for action in actions
                if action.edit.document_changes[0].edits[0].range.start >= pos_range.start
            ])

            checked.add(paragraph)
        self.add_diagnostics(doc, diagnostics)
        self.add_code_actions(doc, code_actions)
