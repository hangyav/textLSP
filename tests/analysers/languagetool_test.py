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
from textLSP.documents.document import BaseDocument
from textLSP.analysers.languagetool import LanguageToolAnalyser

from tests.lsp_test_client import session, utils


@pytest.fixture
def analyser():
    return LanguageToolAnalyser(
        None,
        {},
        'languagetool',
    )


def test_analyse(analyser):
    doc = BaseDocument(
        'tmp.txt',
        'This is a santance.',
        config={},
        version=0
    )
    analyser._analyse(doc.cleaned_source, doc)


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

    langtool_ls_onsave.set_notification_callback(
        session.WINDOW_SHOW_MESSAGE,
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
    assert not done.wait(20)
    done.clear()


def test_bug2(json_converter, langtool_ls_onsave):
    text = (
        'This is a sentence.\n'
        + 'This is a sentence.\n'
        + 'This is a sentence.\n'
    )

    done = Event()
    results = list()

    langtool_ls_onsave.set_notification_callback(
        session.WINDOW_SHOW_MESSAGE,
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

    for i, edit_range in enumerate([
        # Last two sentences deleted as done by nvim
        Range(
            start=Position(line=0, character=19),
            end=Position(line=0, character=19),
        ),
        Range(
            start=Position(line=1, character=0),
            end=Position(line=2, character=0),
        ),
        Range(
            start=Position(line=1, character=0),
            end=Position(line=1, character=19),
        ),
        Range(
            start=Position(line=0, character=19),
            end=Position(line=0, character=19),
        ),
        Range(
            start=Position(line=1, character=0),
            end=Position(line=2, character=0),
        ),
    ], 1):
        change_params = DidChangeTextDocumentParams(
            text_document=VersionedTextDocumentIdentifier(
                version=i,
                uri='dummy.txt',
            ),
            content_changes=[
                TextDocumentContentChangeEvent_Type1(
                    edit_range,
                    '',
                )
            ]
        )
        langtool_ls_onsave.notify_did_change(
            json_converter.unstructure(change_params)
        )

    save_params = DidSaveTextDocumentParams(
        text_document=TextDocumentIdentifier(
            'dummy.txt'
        )
    )
    langtool_ls_onsave.notify_did_save(
        json_converter.unstructure(save_params)
    )
    assert not done.wait(20)
    done.clear()
