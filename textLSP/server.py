import logging

from pygls.server import LanguageServer
from pygls.protocol import LanguageServerProtocol, lsp_method
from pygls.lsp.methods import INITIALIZE
from pygls.lsp.types import InitializeParams, InitializeResult
from lsprotocol.types import (
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_CHANGE,
)
from lsprotocol.types import (
        DidOpenTextDocumentParams,
        DidChangeTextDocumentParams,
)
from .workspace import TextLSPWorkspace


logger = logging.getLogger(__name__)


class TextLSPLanguageServerProtocol(LanguageServerProtocol):
    @lsp_method(INITIALIZE)
    def lsp_initialize(self, params: InitializeParams) -> InitializeResult:
        result = super().lsp_initialize(params)
        self.workspace = TextLSPWorkspace.workspace2textlspworkspace(self.workspace)
        return result


SERVER = LanguageServer(protocol_cls=TextLSPLanguageServerProtocol)


@SERVER.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls, params: DidOpenTextDocumentParams):
    """Text document did open notification."""
    ls.show_message('Text Document Did Open')


@SERVER.feature(TEXT_DOCUMENT_DID_CHANGE)
async def did_change(ls, params: DidChangeTextDocumentParams):
    """Text document did change notification."""
    pass
