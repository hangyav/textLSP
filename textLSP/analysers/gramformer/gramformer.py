import logging

from re import Match
from itertools import chain
from typing import List, Tuple
from gramformer import Gramformer
from lsprotocol.types import (
        Diagnostic,
        Range,
        Position,
        TextEdit,
        CodeAction,
)
from pygls.server import LanguageServer

from ..analyser import Analyser
from ...types import Interval, TEXT_PASSAGE_PATTERN
from ...documents.document import BaseDocument


logger = logging.getLogger(__name__)


class GramformerAnalyser(Analyser):
    CONFIGURATION_GPU = 'gpu'

    SETTINGS_DEFAULT_GPU = False

    def __init__(self, language_server: LanguageServer, config: dict, name: str):
        super().__init__(language_server, config, name)
        try:
            # This could take some time the first time to download models.
            self.analyser = Gramformer(
                models=1,  # 1=corrector, 2=detector
                use_gpu=self.config.get(self.CONFIGURATION_GPU, self.SETTINGS_DEFAULT_GPU),
            )
        except OSError:
            from spacy.cli import download
            download('en')

            self.analyser = Gramformer(
                models=1,  # 1=corrector, 2=detector
                use_gpu=self.config.get(self.CONFIGURATION_GPU, self.SETTINGS_DEFAULT_GPU),
            )

    def _analyse_sentences(self, text, doc, offset=0) -> Tuple[List[Diagnostic], List[CodeAction]]:
        diagnostics = list()
        code_actions = list()

        sidx = 0
        for match in chain(TEXT_PASSAGE_PATTERN.finditer(text), [len(text)]):
            if type(match) == Match:
                eidx = match.end()
            else:
                eidx = match
            if sidx == eidx:
                continue

            sentence = text[sidx:eidx]
            diags, actions = self._analyse(sentence, doc, sidx+offset)
            diagnostics.extend(diags)
            code_actions.extend(actions)

            sidx = eidx

        return diagnostics, code_actions

    def _analyse(self, text, doc, offset=0) -> Tuple[List[Diagnostic], List[CodeAction]]:
        text = text.strip()
        if len(text) == 0:
            return [], []

        diagnostics = list()
        code_actions = list()

        corrected = self.analyser.correct(text, max_candidates=1)
        if len(corrected) > 0:
            edits = self.analyser.get_edits(text, corrected.pop())
            tokenized_text = text.split(' ')

            for edit in edits:
                # edit = (ERROR_CODE, WORD_OLD, OLD_START_POS, OLD_END_POS, WORD_NEW, NEW_START_POS, NEW_END_POS)
                token = edit[1]
                start_pos = 0
                if edit[2] > 0:
                    start_pos = len(' '.join(tokenized_text[:edit[2]])) + 1
                end_pos = len(' '.join(tokenized_text[:edit[3]]))

                range = doc.range_at_offset(
                    start_pos+offset,
                    end_pos-start_pos,
                    True
                )
                range = Range(
                    start=range.start,
                    end=Position(
                        line=range.end.line,
                        character=range.end.character+1,
                    )
                )
                diagnostic = Diagnostic(
                    range=range,
                    message=f'"{token}": Gramformer suggestion',
                    source='gramformer',
                    severity=self.get_severity(),
                    code=f'gramformer:{edit[0]}',
                )
                action = self.build_single_suggestion_action(
                    doc=doc,
                    title=f'"{token}" -> "{edit[4]}"',
                    edit=TextEdit(
                        range=diagnostic.range,
                        new_text=edit[4],
                    ),
                    diagnostic=diagnostic,
                )
                code_actions.append(action)
                diagnostics.append(diagnostic)

        return diagnostics, code_actions

    def _did_open(self, doc: BaseDocument):
        diagnostics, actions = self._analyse_sentences(doc.cleaned_source, doc)
        self.add_diagnostics(doc, diagnostics)
        self.add_code_actions(doc, actions)

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

            pos_range = doc.range_at_offset(
                paragraph.start,
                paragraph.length,
                True
            )
            self.remove_code_items_at_rage(doc, pos_range)

            diags, actions = self._analyse_sentences(
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
