from typing import List
from pygls.server import LanguageServer
from pygls.workspace import Document
from lsprotocol.types import (
        DidOpenTextDocumentParams,
        DidChangeTextDocumentParams,
        DidCloseTextDocumentParams,
        Diagnostic,
        DiagnosticSeverity,
        Range,
)

from ..documents.document import BaseDocument
from ..utils import merge_dicts


class Analyser():
    SEVERITY = 'severity'

    def __init__(self, language_server: LanguageServer, config: dict):
        self.default_severity = DiagnosticSeverity.Information
        self.language_server = language_server
        self.config = dict()
        self.update_settings(config)
        self._diagnostics_dict = dict()

    def did_open(self, params: DidOpenTextDocumentParams):
        raise NotImplementedError()

    def did_change(self, params: DidChangeTextDocumentParams):
        self.did_open(DidOpenTextDocumentParams(
            text_document=params.text_document
        ))

    def did_close(self, params: DidCloseTextDocumentParams):
        pass

    def update_settings(self, settings):
        self.config = merge_dicts(self.config, settings)

    def close(self):
        pass

    def get_document(self, document_descriptor) -> BaseDocument:
        if type(document_descriptor) != str:
            document_descriptor = document_descriptor.text_document.uri
        return self.language_server.workspace.get_document(document_descriptor)

    def get_severity(self) -> DiagnosticSeverity:
        if Analyser.SEVERITY in self.config:
            try:
                return DiagnosticSeverity[self.config[Analyser.SEVERITY]]
            except KeyError:
                pass
        return self.default_severity

    def init_diagnostics(self, doc: Document):
        self._diagnostics_dict[doc.uri] = list()

    def get_diagnostics(self, doc: Document):
        return self._diagnostics_dict.get(doc.uri, list())

    def add_diagnostics(self, doc: Document, diagnostics: List[Diagnostic]):
        self._diagnostics_dict[doc.uri] += diagnostics
        self.language_server.publish_stored_diagnostics(doc)

    def remove_diagnostics_at_rage(self, doc: Document, pos_range: Range):
        diagnostics = list()
        for diag in self.get_diagnostics(doc):
            if diag.range.end < pos_range.start or diag.range.start > pos_range.end:
                diagnostics.append(diag)
        self._diagnostics_dict[doc.uri] = diagnostics


class AnalysisError(Exception):
    pass
