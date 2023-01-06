import logging

from typing import List
from collections import defaultdict
from language_tool_python import LanguageTool
from lsprotocol.types import (
        DidOpenTextDocumentParams,
        DidChangeTextDocumentParams,
        TextDocumentContentChangeEvent_Type2,
        DidCloseTextDocumentParams,
        Diagnostic,
        Range,
        Position,
)
from pygls.server import LanguageServer

from ..analyser import Analyser


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

    def did_open(self, params: DidOpenTextDocumentParams):
        doc = self.get_document(params)
        self.init_diagnostics(doc)
        diagnostics = self._analyse(doc.cleaned_source, doc)
        self.add_diagnostics(doc, diagnostics)

    def did_change(self, params: DidChangeTextDocumentParams):
        # TODO remove
        self.did_open(DidOpenTextDocumentParams(
            text_document=params.text_document
        ))
        return
        if any(
            type(item) == TextDocumentContentChangeEvent_Type2
            for item in params.content_changes
        ):
            self.did_open(DidOpenTextDocumentParams(
                text_document=params.text_document
            ))

        doc = self.get_document(params)
        checked = set()
        diagnostics = list()
        lines = doc.cleaned_lines
        # TODO buggy
        for change in params.content_changes:
            pos_range = change.range
            # if pos_range.end.line + 1 < len(lines):
            #     end = Position(
            #         line=pos_range.end.line+1,
            #         character=0,
            #     )
            # else:
            #     end = Position(
            #         line=pos_range.end.line,
            #         character=max(0, len(lines[-1])-1),
            #     )
            #
            # pos_range = Range(
            #     start=Position(
            #         line=max(0, pos_range.start.line-1),
            #         character=0,
            #     ),
            #     end=end
            # )
            self.remove_diagnostics_at_rage(doc, pos_range)
            for paragraph in doc.paragraphs_at_range(pos_range, True):
                if paragraph in checked:
                    continue

                diags = self._analyse(
                    doc.cleaned_source[paragraph.start:paragraph.start +
                                       paragraph.length],
                    doc,
                    paragraph.start
                )
                diagnostics.extend(diags)
                checked.add(paragraph)
        self.add_diagnostics(doc, diagnostics)

    def did_close(self, params: DidCloseTextDocumentParams):
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
