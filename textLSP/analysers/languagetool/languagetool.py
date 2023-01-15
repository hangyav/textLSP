import logging

from typing import List
from collections import defaultdict
from language_tool_python import LanguageTool
from lsprotocol.types import (
        DidOpenTextDocumentParams,
        TextDocumentContentChangeEvent_Type2,
        Diagnostic,
        Range,
        Position,
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
    def __init__(self, language_server: LanguageServer, config: dict):
        super().__init__(language_server, config)
        self.tools = dict()

    def _analyse(self, text, doc, offset=0) -> List[Diagnostic]:
        diagnostics = list()
        matches = self._get_tool_for_language(doc.language).check(text)

        for match in matches:
            token = text[match.offset:match.offset+match.errorLength]
            replacements = ''
            if len(match.replacements) > 0:
                replacements = ', '.join(item for item in match.replacements)
                replacements = f' -> {replacements}'
            diagnostics.append(
                Diagnostic(
                    range=doc.range_at_offset(match.offset+offset, match.errorLength, True),
                    message=f'"{token}"{replacements}: {match.message}',
                    source='languagetool',
                    severity=self.get_severity(),
                    code=f'languagetool:{match.ruleId}',
                )
            )

        return diagnostics

    def _did_open(self, doc: BaseDocument):
        self.init_diagnostics(doc)
        diagnostics = self._analyse(doc.cleaned_source, doc)
        self.add_diagnostics(doc, diagnostics)

    def _did_change(self, doc: BaseDocument, changes: List[Interval]):
        diagnostics = list()
        checked = set()
        for change in changes:
            # TODO consider checking 1 paragraph before/after for better context
            # based analysis. E.g. currently using a given word 3 times as the
            # first word in a sentence consequtively but with paragraph break
            # in between will not be detected.
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
            self.remove_diagnostics_at_rage(doc, pos_range)

            diags = self._analyse(
                doc.cleaned_source[paragraph.start:paragraph.start +
                                   paragraph.length],
                doc,
                paragraph.start
            )
            diagnostics.extend(diags)
            checked.add(paragraph)
        self.add_diagnostics(doc, diagnostics)

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
