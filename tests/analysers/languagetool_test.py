import pytest

from threading import Event
from lsprotocol.types import (
    DidOpenTextDocumentParams,
    TextDocumentItem,
    DidChangeTextDocumentParams,
    VersionedTextDocumentIdentifier,
    TextDocumentContentChangeEvent_Type1,
    Range,
    Position,
    DidSaveTextDocumentParams,
    TextDocumentIdentifier,
)

from tests.lsp_test_client import session, utils


@pytest.mark.skip(reason="Not finished. See TODO below.")
def test_bug1(json_converter, langtool_ls_onsave):
    text = ('\\documentclass[11pt]{article}\n'
            + '\\begin{document}\n'
            + '\n'
            + '\\section{Introduction}\n'
            + '\n'
            + 'This is a sentence.\n'
            + '\n'
            + '\\end{document}')

    done = Event()
    results = list()

    # TODO This should wait for error messages from the server. The test should
    # not cause any server errors.
    langtool_ls_onsave.set_notification_callback(
        session.WINDOW_LOG_MESSAGE,
        utils.get_notification_handler(
            event=done,
            results=results
        ),
    )

    open_params = DidOpenTextDocumentParams(
        TextDocumentItem(
            uri='dummy.tex',
            language_id='tex',
            version=1,
            text=text,
        )
    )

    langtool_ls_onsave.notify_did_open(
        json_converter.unstructure(open_params)
    )

    change_params = DidChangeTextDocumentParams(
        text_document=VersionedTextDocumentIdentifier(
            version=1,
            uri='dummy.tex',
        ),
        content_changes=[
            TextDocumentContentChangeEvent_Type1(
                Range(
                    start=Position(line=5, character=19),
                    end=Position(line=6, character=0),
                ),
                '\nThis is a sentence.\n',
            )
        ]
    )
    langtool_ls_onsave.notify_did_change(
        json_converter.unstructure(change_params)
    )

    change_params = DidChangeTextDocumentParams(
        text_document=VersionedTextDocumentIdentifier(
            version=2,
            uri='dummy.tex',
        ),
        content_changes=[
            TextDocumentContentChangeEvent_Type1(
                Range(
                    start=Position(line=6, character=19),
                    end=Position(line=7, character=0),
                ),
                '\nThis is a sentence.\n',
            )
        ]
    )
    langtool_ls_onsave.notify_did_change(
        json_converter.unstructure(change_params)
    )

    save_params = DidSaveTextDocumentParams(
        text_document=TextDocumentIdentifier(
            'dummy.tex'
        )
    )
    langtool_ls_onsave.notify_did_save(
        json_converter.unstructure(save_params)
    )
    assert done.wait(30)
    done.clear()
