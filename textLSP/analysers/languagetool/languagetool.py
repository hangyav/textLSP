import logging

from collections import defaultdict
from language_tool_python import LanguageTool
from lsprotocol.types import (
        DidOpenTextDocumentParams,
        DidChangeTextDocumentParams,
        DidCloseTextDocumentParams,
        Diagnostic,
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

    def did_open(self, params: DidOpenTextDocumentParams):
        diagnostics = list()
        doc = self.get_document(params)
        source = doc.cleaned_source
        matches = self._get_tool_for_language(doc.language).check(source)

        for match in matches:
            token = source[match.offset:match.offset+match.errorLength]
            diagnostics.append(
                Diagnostic(
                    range=doc.range_at_offset(match.offset, match.errorLength, True),
                    message=f'"{token}": {match.message}',
                    source='languagetool',
                    severity=self.get_severity(),
                    code=match.ruleId,
                )
            )

        self.language_server.publish_diagnostics(doc.uri, diagnostics)

    def did_change(self, params: DidChangeTextDocumentParams):
        # TODO
        self.did_open(DidOpenTextDocumentParams(
            text_document=params.text_document
        ))

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
