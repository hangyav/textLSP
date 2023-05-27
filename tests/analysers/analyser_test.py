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
)

from tests.lsp_test_client import session, utils


@pytest.mark.parametrize('text,edit,exp', [
    (
        'This is a sentence.\n'
        'This is a sAntence with an error.\n'
        'This is another sentence.',
        (
            Range(
                start=Position(line=2, character=0),
                end=Position(line=2, character=0),
            ),
            '\n',
        ),
        Range(
            start=Position(line=1, character=10),
            end=Position(line=1, character=18),
        ),
    ),
    (
        'This is a sentence.\n'
        'This is a sAntence with an error.\n'
        'This is another sentence.',
        (
            Range(
                start=Position(line=0, character=0),
                end=Position(line=0, character=0),
            ),
            '\n\n\n',
        ),
        Range(
            start=Position(line=4, character=10),
            end=Position(line=4, character=18),
        ),
    ),
    (
        'This is a sentence.\n'
        'This is a sAntence with an error.\n'
        'This is another sentence.',
        (
            Range(
                start=Position(line=1, character=23),
                end=Position(line=1, character=23),
            ),
            '\n',
        ),
        Range(
            start=Position(line=1, character=10),
            end=Position(line=1, character=18),
        ),
    ),
])
def test_diagnostics_line_shifts(text, edit, exp, json_converter, langtool_ls_onsave):
    done = Event()
    results = list()

    langtool_ls_onsave.set_notification_callback(
        session.PUBLISH_DIAGNOSTICS,
        utils.get_notification_handler(
            event=done,
            results=results
        ),
    )

    open_params = DidOpenTextDocumentParams(
        TextDocumentItem(
            uri='dummy.txt',
            language_id='txt',
            version=1,
            text=text,
        )
    )

    langtool_ls_onsave.notify_did_open(
        json_converter.unstructure(open_params)
    )
    done.wait()
    done.clear()

    change_params = DidChangeTextDocumentParams(
        text_document=VersionedTextDocumentIdentifier(
            version=1,
            uri='dummy.txt',
        ),
        content_changes=[
            TextDocumentContentChangeEvent_Type1(
                edit[0],
                edit[1],
            )
        ]
    )
    langtool_ls_onsave.notify_did_change(
        json_converter.unstructure(change_params)
    )

    done.wait()
    done.clear()

    res = results[-1]['diagnostics'][0]['range']
    assert res == json_converter.unstructure(exp)
