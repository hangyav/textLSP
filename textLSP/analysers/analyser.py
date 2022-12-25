from pygls.server import LanguageServer
from lsprotocol.types import (
        DidOpenTextDocumentParams,
        DidChangeTextDocumentParams,
        DidCloseTextDocumentParams,
        DiagnosticSeverity,
)

from ..workspace import BaseDocument
from ..utils import merge_dicts


class Analyser():
    SEVERITY = 'severity'

    def __init__(self, language_server: LanguageServer, config: dict):
        self.default_severity = DiagnosticSeverity.Information
        self.language_server = language_server
        self.config = dict()
        self.update_settings(config)

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
