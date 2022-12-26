import logging

from pygls.server import LanguageServer
from pygls.protocol import LanguageServerProtocol, lsp_method
from lsprotocol.types import (
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    WORKSPACE_DID_CHANGE_CONFIGURATION,
    INITIALIZE,
)
from lsprotocol.types import (
        DidOpenTextDocumentParams,
        DidChangeTextDocumentParams,
        DidChangeConfigurationParams,
        DidCloseTextDocumentParams,
        InitializeParams,
        InitializeResult
)
from .workspace import TextLSPWorkspace
from .utils import merge_dicts, get_textlsp_version
from .analysers.handler import AnalyserHandler


logger = logging.getLogger(__name__)


class TextLSPLanguageServerProtocol(LanguageServerProtocol):
    @lsp_method(INITIALIZE)
    def lsp_initialize(self, params: InitializeParams) -> InitializeResult:
        result = super().lsp_initialize(params)
        self.workspace = TextLSPWorkspace.workspace2textlspworkspace(self.workspace)
        self._server.update_settings(params.initialization_options)
        return result


class TextLSPLanguageServer(LanguageServer):
    CONFIGURATION_SECTION = 'textLSP'
    CONFIGURATION_ANALYSERS = 'analysers'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = dict()
        self.analyser_handler = AnalyserHandler(self)

    def get_analyser_settings(self, settings=None):
        if settings is None:
            settings = self.settings

        if (
            self.CONFIGURATION_SECTION in settings and
            self.CONFIGURATION_ANALYSERS in settings[self.CONFIGURATION_SECTION]
        ):
            return self.settings[self.CONFIGURATION_SECTION][self.CONFIGURATION_ANALYSERS]
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


SERVER = TextLSPLanguageServer(
    name='textLSP',
    version=get_textlsp_version(),
    protocol_cls=TextLSPLanguageServerProtocol,
)


@SERVER.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls, params: DidOpenTextDocumentParams):
    await ls.analyser_handler.did_open(params)


@SERVER.feature(TEXT_DOCUMENT_DID_CHANGE)
async def did_change(ls, params: DidChangeTextDocumentParams):
    await ls.analyser_handler.did_change(params)


@SERVER.feature(TEXT_DOCUMENT_DID_CLOSE)
async def did_close(ls, params: DidCloseTextDocumentParams):
    await ls.analyser_handler.did_close(params)


@SERVER.feature(WORKSPACE_DID_CHANGE_CONFIGURATION)
def did_change_configuration(ls, params: DidChangeConfigurationParams):
    ls.update_settings(params.settings)
