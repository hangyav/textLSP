from typing import List
from pygls.server import LanguageServer
from pygls.workspace import Document
from lsprotocol.types import (
        DidOpenTextDocumentParams,
        DidChangeTextDocumentParams,
        DidCloseTextDocumentParams,
        DidSaveTextDocumentParams,
        Diagnostic,
        DiagnosticSeverity,
        Range,
)

from ..documents.document import BaseDocument
from ..utils import merge_dicts


class Analyser():
    CONFIGURATION_SEVERITY = 'severity'
    CONFIGURATION_CHECK = 'check_text'
    CONFIGURATION_CHECK_ON_OPEN = 'on_open'
    CONFIGURATION_CHECK_ON_CHANGE = 'on_change'
    CONFIGURATION_CHECK_ON_SAVE = 'on_save'

    SETTINGS_DEFAULT_CHECK_ON = {
        CONFIGURATION_CHECK_ON_OPEN: True,
        CONFIGURATION_CHECK_ON_CHANGE: False,
        CONFIGURATION_CHECK_ON_SAVE: True,
    }

    def __init__(self, language_server: LanguageServer, config: dict):
        self.default_severity = DiagnosticSeverity.Information
        self.language_server = language_server
        self.config = dict()
        self.update_settings(config)
        self._diagnostics_dict = dict()

    def _did_open(self, doc: Document):
        raise NotImplementedError()

    def did_open(self, params: DidOpenTextDocumentParams):
        if self.should_run_on(Analyser.CONFIGURATION_CHECK_ON_OPEN):
            self._did_open(self.get_document(params))

    def _did_change(self, doc: Document):
        self.did_open(DidOpenTextDocumentParams(
            text_document=doc
        ))

    def did_change(self, params: DidChangeTextDocumentParams):
        if self.should_run_on(Analyser.CONFIGURATION_CHECK_ON_CHANGE):
            self._did_change(self.get_document(params))

    def did_save(self, params: DidSaveTextDocumentParams):
        if self.should_run_on(Analyser.CONFIGURATION_CHECK_ON_SAVE):
            self._did_change(self.get_document(params))

    def _did_close(self, doc: Document):
        pass

    def did_close(self, params: DidCloseTextDocumentParams):
        self._did_close(self.get_document(params))

    def update_settings(self, settings):
        self.config = merge_dicts(self.config, settings)

    def close(self):
        pass

    def get_document(self, document_descriptor) -> BaseDocument:
        if type(document_descriptor) != str:
            document_descriptor = document_descriptor.text_document.uri
        return self.language_server.workspace.get_document(document_descriptor)

    def get_severity(self) -> DiagnosticSeverity:
        if Analyser.CONFIGURATION_SEVERITY in self.config:
            try:
                return DiagnosticSeverity[self.config[Analyser.CONFIGURATION_SEVERITY]]
            except KeyError:
                pass
        return self.default_severity

    def should_run_on(self, event: str) -> bool:
        return self.config.setdefault(
                Analyser.CONFIGURATION_CHECK,
                dict()
        ).setdefault(
            event,
            Analyser.SETTINGS_DEFAULT_CHECK_ON.setdefault(
                event,
                False,
            )
        )

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
