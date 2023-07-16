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
    CodeActionParams,
    CodeActionContext,
    Diagnostic,
)

from tests.lsp_test_client import session, utils


@pytest.mark.parametrize('text,edit,exp', [
    (
        'This is a sentence.\n'
        'This is a sAntence with an error.\n'
        'And another sentence.',
        (
            Range(
                start=Position(line=2, character=0),
                end=Position(line=2, character=0),
            ),
            '\n',
            False
        ),
        Range(
            start=Position(line=1, character=10),
            end=Position(line=1, character=18),
        ),
    ),
    (
        'This is a sentence.\n'
        'This is a sAntence with an error.\n'
        'And another sentence.',
        (
            Range(
                start=Position(line=0, character=0),
                end=Position(line=0, character=0),
            ),
            '\n\n\n',
            True
        ),
        Range(
            start=Position(line=4, character=10),
            end=Position(line=4, character=18),
        ),
    ),
    (
        'This is a sentence.\n'
        'This is a sAntence with an error.\n'
        'And another sentence.',
        (
            Range(
                start=Position(line=0, character=0),
                end=Position(line=1, character=0),
            ),
            '',
            True
        ),
        Range(
            start=Position(line=0, character=10),
            end=Position(line=0, character=18),
        ),
    ),
    (
        'This is a sentence.\n'
        'This is a sAntence with an error.\n'
        'And another sentence.',
        (
            Range(
                start=Position(line=1, character=23),
                end=Position(line=1, character=23),
            ),
            '\n',
            False
        ),
        Range(
            start=Position(line=1, character=10),
            end=Position(line=1, character=18),
        ),
    ),
    (
        'This is a sentence.\n'
        'This is a sAntence with an error.\n'
        'And another sentence.',
        (
            Range(
                start=Position(line=1, character=33),
                end=Position(line=1, character=33),
            ),
            ' too',
            False
        ),
        Range(
            start=Position(line=1, character=10),
            end=Position(line=1, character=18),
        ),
    ),
    (
        'This is a sentence.\n'
        'This is a sAntence with an error.\n'
        'And another sentence.',
        (
            Range(
                start=Position(line=1, character=4),
                end=Position(line=1, character=4),
            ),
            ' word',
            True
        ),
        Range(
            start=Position(line=1, character=15),
            end=Position(line=1, character=23),
        ),
    ),
    (
        'This is a sentence.\n'
        'This is a sAntence with an error.\n'
        'And another sentence.',
        (
            Range(
                start=Position(line=1, character=4),
                end=Position(line=1, character=4),
            ),
            '\n',
            True
        ),
        Range(
            start=Position(line=2, character=5),
            end=Position(line=2, character=13),
        ),
    ),
])
def test_line_shifts(text, edit, exp, json_converter, langtool_ls_onsave):
    done = Event()
    diag_lst = list()

    langtool_ls_onsave.set_notification_callback(
        session.PUBLISH_DIAGNOSTICS,
        utils.get_notification_handler(
            event=done,
            results=diag_lst
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
    assert done.wait(30)
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
    ret = done.wait(1)
    done.clear()

    # no diagnostics notification of none has changed
    assert ret == edit[2]
    if edit[2]:
        assert len(diag_lst) == 2
    else:
        assert len(diag_lst) == 1

    res = diag_lst[-1]['diagnostics'][0]['range']
    assert res == json_converter.unstructure(exp)

    diag = diag_lst[-1]['diagnostics'][0]
    diag = Diagnostic(
        range=Range(
            start=Position(**res['start']),
            end=Position(**res['end']),
        ),
        message=diag['message'],
    )
    code_action_params = CodeActionParams(
        TextDocumentIdentifier('dummy.txt'),
        exp,
        CodeActionContext([diag]),
    )
    actions_lst = langtool_ls_onsave.text_document_code_action(
        json_converter.unstructure(code_action_params)
    )
    assert len(actions_lst) == 1
    res = actions_lst[-1]['diagnostics'][0]['range']
    assert res == json_converter.unstructure(exp)


@pytest.mark.parametrize('text,edit,exp', [
    (
        'Introduction\n'
        '\n'
        'This is a sentence.\n'
        'This is another.\n'
        '\n'
        'Thes is bold.',
        (
            Range(
                start=Position(line=1, character=0),
                end=Position(line=1, character=0),
            ),
            '\n\n',
        ),
        Range(
            start=Position(line=7, character=0),
            end=Position(line=7, character=7),
        ),
    ),
])
def test_diagnostics_bug1(text, edit, exp, json_converter, langtool_ls_onsave):
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
    assert done.wait(30)
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
    assert done.wait(30)
    done.clear()

    save_params = DidSaveTextDocumentParams(
        text_document=TextDocumentIdentifier(
            'dummy.txt'
        )
    )
    langtool_ls_onsave.notify_did_save(
        json_converter.unstructure(save_params)
    )
    assert done.wait(30)
    done.clear()

    res = results[-1]['diagnostics'][0]['range']
    assert res == json_converter.unstructure(exp)


def test_diagnostics_bug2(json_converter, langtool_ls_onsave):
    text = ('\\documentclass[11pt]{article}\n'
            + '\\begin{document}\n'
            + 'o\n'
            + '\\section{Thes}\n'
            + '\n'
            + 'This is a sentence.\n'
            + '\n'
            + '\\end{document}')

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
            uri='dummy.tex',
            language_id='tex',
            version=1,
            text=text,
        )
    )

    langtool_ls_onsave.notify_did_open(
        json_converter.unstructure(open_params)
    )
    assert done.wait(30)
    done.clear()

    change_params = DidChangeTextDocumentParams(
        text_document=VersionedTextDocumentIdentifier(
            version=1,
            uri='dummy.tex',
        ),
        content_changes=[
            TextDocumentContentChangeEvent_Type1(
                Range(
                    start=Position(line=2, character=0),
                    end=Position(line=3, character=0),
                ),
                '',
            )
        ]
    )
    langtool_ls_onsave.notify_did_change(
        json_converter.unstructure(change_params)
    )
    assert done.wait(30)
    done.clear()

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

    change_params = DidChangeTextDocumentParams(
        text_document=VersionedTextDocumentIdentifier(
            version=2,
            uri='dummy.tex',
        ),
        content_changes=[
            TextDocumentContentChangeEvent_Type1(
                Range(
                    start=Position(line=1, character=16),
                    end=Position(line=2, character=0),
                ),
                '\no\n',
            )
        ]
    )
    langtool_ls_onsave.notify_did_change(
        json_converter.unstructure(change_params)
    )
    assert done.wait(30)
    done.clear()

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

    exp_lst = [
        Range(
            start=Position(line=2, character=0),
            end=Position(line=2, character=1),
        ),
        Range(
            start=Position(line=3, character=9),
            end=Position(line=3, character=13),
        ),
    ]
    res_lst = results[-1]['diagnostics']
    assert len(res_lst) == len(exp_lst)
    for exp, res in zip(exp_lst, res_lst):
        assert res['range'] == json_converter.unstructure(exp)
