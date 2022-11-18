import logging

from pygls.server import LanguageServer
from pygls.protocol import LanguageServerProtocol
from pygls.capabilities import COMPLETION
from pygls.lsp import CompletionItem, CompletionList, CompletionOptions, CompletionParams


logger = logging.getLogger(__name__)


SERVER = LanguageServer(protocol_cls=LanguageServerProtocol)


@SERVER.feature(COMPLETION, CompletionOptions(trigger_characters=[',']))
def completions(params: CompletionParams):
    """Returns completion items."""
    logger.warning('ASD')
    return CompletionList(
        is_incomplete=False,
        items=[
            CompletionItem(label='"'),
            CompletionItem(label='['),
            CompletionItem(label=']'),
            CompletionItem(label='{'),
            CompletionItem(label='}'),
        ]
    )
