import logging

from typing import List, Tuple
from collections import defaultdict
from language_tool_python import LanguageTool
from lsprotocol.types import (
        Diagnostic,
        Range,
        Position,
        TextEdit,
        CodeAction,
)
from pygls.server import LanguageServer

from ..analyser import Analyser
from ...types import Interval
from ...documents.document import BaseDocument


logger = logging.getLogger(__name__)


LANGUAGE_MAP = defaultdict(lambda: 'en-US')
LANGUAGE_MAP['en'] = 'en-US'
LANGUAGE_MAP['en-US'] = 'en-US'


class LanguageToolAnalyser(Analyser):
    def __init__(self, language_server: LanguageServer, config: dict, name: str):
        super().__init__(language_server, config, name)
        self.tools = dict()

    def _analyse(self, text, doc, offset=0) -> Tuple[List[Diagnostic], List[CodeAction]]:
        diagnostics = list()
        code_actions = list()
        matches = self._get_tool_for_language(doc.language).check(text)

        for match in matches:
            token = text[match.offset:match.offset+match.errorLength]

            range = doc.range_at_offset(match.offset+offset, match.errorLength, True)
            range = Range(
                start=range.start,
                end=Position(
                    line=range.end.line,
                    character=range.end.character+1,
                )
            )
            diagnostic = Diagnostic(
                range=range,
                message=f'"{token}": {match.message}',
                source='languagetool',
                severity=self.get_severity(),
                code=f'languagetool:{match.ruleId}',
            )
            if len(match.replacements) > 0:
                for replacement in match.replacements:
                    action = self.build_single_suggestion_action(
                        doc=doc,
                        title=f'"{token}" -> "{replacement}"',
                        edit=TextEdit(
                            range=diagnostic.range,
                            new_text=replacement,
                        ),
                        diagnostic=diagnostic,
                    )
                    code_actions.append(action)
            diagnostics.append(diagnostic)

        return diagnostics, code_actions

    def _did_open(self, doc: BaseDocument):
        diagnostics, actions = self._analyse(doc.cleaned_source, doc)
        self.add_diagnostics(doc, diagnostics)
        self.add_code_actions(doc, actions)

    def _did_change(self, doc: BaseDocument, changes: List[Interval]):
        diagnostics = list()
        code_actions = list()
        checked = set()
        doc_length = len(doc.cleaned_source)
        for change in changes:
            paragraph = doc.paragraph_at_offset(
                change.start,
                min_length=change.length,
                cleaned=True,
            )
            if paragraph in checked:
                continue

            # get sentences before paragraph for context check
            n = 2
            min_sent_len = 4
            start_sent = paragraph
            while n > 0:
                pos = start_sent.start - 1 - min_sent_len
                if pos < 0:
                    break

                start_sent = doc.sentence_at_offset(
                    pos,
                    min_length=min_sent_len,
                    cleaned=True
                )
                if len(doc.text_at_offset(start_sent.start, start_sent.length, True).strip()) > 0:
                    n -= 1

            # get sentences after paragraph for context check
            n = 2
            end_sent = paragraph
            while n > 0:
                pos = end_sent.start + end_sent.length
                if pos >= doc_length:
                    break

                end_sent = doc.sentence_at_offset(
                    pos,
                    min_length=min_sent_len,
                    cleaned=True
                )
                if len(doc.text_at_offset(end_sent.start, end_sent.length, True).strip()) > 0:
                    n -= 1
            ###################################################################

            pos_range = doc.range_at_offset(
                paragraph.start,
                end_sent.start-paragraph.start-1 + end_sent.length,
                True
            )
            self.remove_code_items_at_rage(doc, pos_range)

            diags, actions = self._analyse(
                doc.text_at_offset(
                    start_sent.start,
                    end_sent.start-start_sent.start-1 + end_sent.length,
                    True
                ),
                doc,
                start_sent.start,
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

    def _did_close(self, doc: BaseDocument):
        workspace = self.language_server.workspace
        doc_langs = {
            document.language
            for _, document in workspace.documents.items()
        }
        tool_langs = set(self.tools.keys())

        for lang in tool_langs - doc_langs:
            self.tools[lang].close()
            del self.tools[lang]

    def close(self):
        for lang, tool in self.tools.items():
            tool.close()
        self.tool = dict()

    def _get_mapped_language(self, language):
        return LANGUAGE_MAP[language]

    def _get_tool_for_language(self, language):
        lang = self._get_mapped_language(language)
        if lang in self.tools:
            return self.tools[lang]

        tool = LanguageTool(lang)
        self.tools[lang] = tool

        return tool
