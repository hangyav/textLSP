import logging

from pygls.server import LanguageServer
from pygls.protocol import LanguageServerProtocol, lsp_method
from lsprotocol.types import (
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_SAVE,
    WORKSPACE_DID_CHANGE_CONFIGURATION,
    INITIALIZE,
)
from lsprotocol.types import (
        DidOpenTextDocumentParams,
        DidChangeTextDocumentParams,
        DidSaveTextDocumentParams,
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
    # TODO make a config class for easier settings hangling and option for
    # settings keys such as textLSP.check_text.on_edit
    CONFIGURATION_SECTION = 'textLSP'
    CONFIGURATION_ANALYSERS = 'analysers'
    # TODO make this configurable per analyser as well
    CONFIGURATION_CHECK = 'check_text'
    CONFIGURATION_CHECK_ON_OPEN = 'on_open'
    CONFIGURATION_CHECK_ON_EDIT = 'on_edit'
    CONFIGURATION_CHECK_ON_SAVE = 'on_save'

    SETTINGS_DEFAULT_CHECK_ON_OPEN = True
    SETTINGS_DEFAULT_CHECK_ON_EDIT = False
    SETTINGS_DEFAULT_CHECK_ON_SAVE = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = dict()
        self.init_settings()
        self.analyser_handler = AnalyserHandler(self)

    def init_settings(self):
        self.settings.setdefault(self.CONFIGURATION_SECTION, dict())
        self.settings[self.CONFIGURATION_SECTION].setdefault(self.CONFIGURATION_ANALYSERS, None)
        self.settings[self.CONFIGURATION_SECTION].setdefault(self.CONFIGURATION_CHECK, dict())
        self.settings[self.CONFIGURATION_SECTION][self.CONFIGURATION_CHECK].setdefault(self.CONFIGURATION_CHECK_ON_OPEN, self.SETTINGS_DEFAULT_CHECK_ON_OPEN)
        self.settings[self.CONFIGURATION_SECTION][self.CONFIGURATION_CHECK].setdefault(self.CONFIGURATION_CHECK_ON_EDIT, self.SETTINGS_DEFAULT_CHECK_ON_EDIT)
        self.settings[self.CONFIGURATION_SECTION][self.CONFIGURATION_CHECK].setdefault(self.CONFIGURATION_CHECK_ON_SAVE, self.SETTINGS_DEFAULT_CHECK_ON_SAVE)

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
    if ls.settings[ls.CONFIGURATION_SECTION][ls.CONFIGURATION_CHECK][ls.CONFIGURATION_CHECK_ON_OPEN]:
        await ls.analyser_handler.did_open(params)


@SERVER.feature(TEXT_DOCUMENT_DID_CHANGE)
async def did_change(ls, params: DidChangeTextDocumentParams):
    if ls.settings[ls.CONFIGURATION_SECTION][ls.CONFIGURATION_CHECK][ls.CONFIGURATION_CHECK_ON_EDIT]:
        await ls.analyser_handler.did_change(params)


@SERVER.feature(TEXT_DOCUMENT_DID_SAVE)
async def did_save(ls, params: DidSaveTextDocumentParams):
    if (
            not ls.settings[ls.CONFIGURATION_SECTION][ls.CONFIGURATION_CHECK][ls.CONFIGURATION_CHECK_ON_EDIT]
            and ls.settings[ls.CONFIGURATION_SECTION][ls.CONFIGURATION_CHECK][ls.CONFIGURATION_CHECK_ON_SAVE]
    ):
        # TODO this is a bit wasteful. We should only check changed parts
        # similar to did_change
        await ls.analyser_handler.did_open(
            DidOpenTextDocumentParams(params.text_document)
        )


@SERVER.feature(TEXT_DOCUMENT_DID_CLOSE)
async def did_close(ls, params: DidCloseTextDocumentParams):
    await ls.analyser_handler.did_close(params)


@SERVER.feature(WORKSPACE_DID_CHANGE_CONFIGURATION)
def did_change_configuration(ls, params: DidChangeConfigurationParams):
    ls.update_settings(params.settings)
