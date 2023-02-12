import logging

from typing import List, Optional
from pygls.server import LanguageServer
from pygls.protocol import LanguageServerProtocol, lsp_method
from pygls.workspace import Document
from lsprotocol.types import (
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_SAVE,
    TEXT_DOCUMENT_CODE_ACTION,
    WORKSPACE_DID_CHANGE_CONFIGURATION,
    INITIALIZE,
    TEXT_DOCUMENT_COMPLETION,
)
from lsprotocol.types import (
    DidOpenTextDocumentParams,
    DidChangeTextDocumentParams,
    DidSaveTextDocumentParams,
    DidChangeConfigurationParams,
    DidCloseTextDocumentParams,
    InitializeParams,
    InitializeResult,
    CodeActionParams,
    CodeActionKind,
    CodeActionOptions,
    CodeAction,
    CompletionList,
    CompletionOptions,
    CompletionParams,
)
from .workspace import TextLSPWorkspace
from .utils import merge_dicts, get_textlsp_version
from .analysers.handler import AnalyserHandler


logger = logging.getLogger(__name__)


class TextLSPLanguageServerProtocol(LanguageServerProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @lsp_method(INITIALIZE)
    def lsp_initialize(self, params: InitializeParams) -> InitializeResult:
        result = super().lsp_initialize(params)
        self.workspace = TextLSPWorkspace.workspace2textlspworkspace(
            self.workspace,
            self._server.analyser_handler,
            self._server.settings,
        )
        self._server.update_settings(params.initialization_options)
        return result


class TextLSPLanguageServer(LanguageServer):
    # TODO make a config class for easier settings hangling and option for
    # settings keys such as textLSP.check_text.on_edit
    CONFIGURATION_SECTION = 'textLSP'
    CONFIGURATION_ANALYSERS = 'analysers'
    CONFIGURATION_DOCUMENTS = 'documents'

    COMMAND_ANALYSE = 'analyse'
    COMMAND_CUSTOM = 'custom_command'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = dict()
        self.init_settings()
        self.analyser_handler = AnalyserHandler(self)

    def init_settings(self):
        self.settings.setdefault(self.CONFIGURATION_SECTION, dict())
        self.settings[self.CONFIGURATION_SECTION].setdefault(self.CONFIGURATION_ANALYSERS, None)
        self.settings[self.CONFIGURATION_SECTION].setdefault(self.CONFIGURATION_DOCUMENTS, None)

    def get_analyser_settings(self, settings=None):
        if settings is None:
            settings = self.settings

        if (
            self.CONFIGURATION_SECTION in settings and
            self.CONFIGURATION_ANALYSERS in settings[self.CONFIGURATION_SECTION]
        ):
            return self.settings[self.CONFIGURATION_SECTION][self.CONFIGURATION_ANALYSERS]
        return None

    def get_document_settings(self, settings=None):
        if settings is None:
            settings = self.settings

        if (
            self.CONFIGURATION_SECTION in settings and
            self.CONFIGURATION_DOCUMENTS in settings[self.CONFIGURATION_SECTION]
        ):
            return self.settings[self.CONFIGURATION_SECTION][self.CONFIGURATION_DOCUMENTS]
        return None

    def update_settings(self, settings):
        if settings is None or len(settings) == 0:
            return
        self.settings = merge_dicts(self.settings, settings)
        if self.get_analyser_settings(settings):
            # update only if there was any update related to it
            self.analyser_handler.update_settings(
                self.get_analyser_settings()
            )
        if self.get_document_settings(settings):
            # update only if there was any update related to it
            self.lsp.workspace.update_settings(
                self.get_document_settings()
            )

    def publish_stored_diagnostics(self, doc: Document):
        diagnostics = list()
        for lst in self.analyser_handler.get_diagnostics(doc):
            diagnostics.extend(lst)
        self.publish_diagnostics(doc.uri, diagnostics)


SERVER = TextLSPLanguageServer(
    name='textLSP',
    version=get_textlsp_version(),
    protocol_cls=TextLSPLanguageServerProtocol,
)


@SERVER.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls: TextLSPLanguageServer, params: DidOpenTextDocumentParams):
    await ls.analyser_handler.did_open(params)


@SERVER.feature(TEXT_DOCUMENT_DID_CHANGE)
async def did_change(ls: TextLSPLanguageServer, params: DidChangeTextDocumentParams):
    await ls.analyser_handler.did_change(params)


@SERVER.feature(TEXT_DOCUMENT_DID_SAVE)
async def did_save(ls: TextLSPLanguageServer, params: DidSaveTextDocumentParams):
    await ls.analyser_handler.did_save(params)


@SERVER.feature(TEXT_DOCUMENT_DID_CLOSE)
async def did_close(ls: TextLSPLanguageServer, params: DidCloseTextDocumentParams):
    await ls.analyser_handler.did_close(params)


@SERVER.feature(WORKSPACE_DID_CHANGE_CONFIGURATION)
def did_change_configuration(ls: TextLSPLanguageServer, params: DidChangeConfigurationParams):
    ls.update_settings(params.settings)


@SERVER.feature(
    TEXT_DOCUMENT_CODE_ACTION,
    CodeActionOptions(
        code_action_kinds=[
            CodeActionKind.QuickFix,
        ],
    ),
)
def code_action(
    ls: TextLSPLanguageServer,
    params: CodeActionParams
) -> Optional[List[CodeAction]]:
    return ls.analyser_handler.get_code_actions(params)


@SERVER.command(TextLSPLanguageServer.COMMAND_ANALYSE)
async def command_analyse(ls: TextLSPLanguageServer, *args):
    await ls.analyser_handler.command_analyse(*args)


@SERVER.command(TextLSPLanguageServer.COMMAND_CUSTOM)
async def command_custom_command(ls: TextLSPLanguageServer, *args):
    await ls.analyser_handler.command_custom_command(*args)


@SERVER.feature(
    TEXT_DOCUMENT_COMPLETION,
    CompletionOptions(trigger_characters=[' '])
)
def completions(
    ls: TextLSPLanguageServer,
    params: Optional[CompletionParams] = None
) -> CompletionList:
    return ls.analyser_handler.get_completions(params)
