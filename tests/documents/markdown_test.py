import pytest

from textLSP.documents.markdown.markdown import MarkDownDocument
from lsprotocol.types import (
    Position,
    Range,
    TextDocumentContentChangeEvent_Type1
)


@pytest.mark.parametrize('src,clean', [
    (
        '# Headline\n'
        'This is a sentence.',
        #
        'Headline\n'
        '\n'
        'This is a sentence.\n'
    ),
    (
        '# Headline\n'
        'This is a sentence.\n'
        'And another in this paragraph.\n'
        '\n'
        'This is another paragraph.',
        #
        'Headline\n'
        '\n'
        'This is a sentence. And another in this paragraph.\n'
        '\n'
        'This is another paragraph.\n'
    ),
    (
        '# Headline\n'
        '   This is a sentence.',
        #
        'Headline\n'
        '\n'
        'This is a sentence.\n'
    ),
    (
        '* Item1\n'
        '* Item2\n'
        '* Item3',
        #
        'Item1\n'
        '\n'
        'Item2\n'
        '\n'
        'Item3\n'
    ),
    (
        '[This is a link](https://www.example.com)',
        #
        'This is a link\n'
    ),
    (
        '~~This~~ is a *bold* **word**.',
        #
        'This is a bold word.\n'
    ),
    (
        '| foo | bar |\n'
        '| --- | --- |\n'
        '| baz | bim |',
        #
        'foo\n'
        '\n'
        'bar\n'
        '\n'
        'baz\n'
        '\n'
        'bim\n'
    ),
])
def test_clean(src, clean):
    doc = MarkDownDocument(
        'tmp.md',
        src,
        config={}
    )

    assert doc.cleaned_source == clean


@pytest.mark.parametrize('src,offset,exp', [
    (
        'This is a sentence.\n',
        # (offset, length)
        (0, 4),
        'This',
    ),
])
def test_highlight(src, offset, exp):
    doc = MarkDownDocument(
        'tmp.md',
        src,
    )

    pos_range = doc.range_at_offset(offset[0], offset[1], True)

    lines = src.splitlines(True)
    if pos_range.start.line == pos_range.end.line:
        res = lines[pos_range.start.line][pos_range.start.character:pos_range.end.character+1]
    else:
        res = lines[pos_range.start.line][pos_range.start.character:]
        res += ''.join([lines[idx] for idx in range(pos_range.start.line+1, pos_range.end.line)])
        res += lines[pos_range.end.line][:pos_range.end.character+1]

    assert res == exp


@pytest.mark.parametrize('content,changes,exp,offset_test,position_test', [
    (
        'This is a sentence.',
        [
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(
                        line=0,
                        character=0,
                    ),
                    end=Position(
                        line=0,
                        character=4,
                    ),
                ),
                text='That',
            ),
        ],
        'That is a sentence.\n',
        None,
        None,
    ),
    (
        # Based on a bug, as done by in nvim
        'This is a sentence. This is another.\n'
        '\n'
        'This is a new paragraph.\n',
        [
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=0, character=19),
                    end=Position(line=0, character=36)
                ),
                text='',
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=1, character=0),
                    end=Position(line=2, character=0)
                ),
                text='',
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=1, character=0),
                    end=Position(line=1, character=24)
                ),
                text='',
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=0, character=19),
                    end=Position(line=0, character=19)
                ),
                text='',
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=1, character=0),
                    end=Position(line=2, character=0)
                ),
                text='',
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=0, character=19),
                    end=Position(line=1, character=0)
                ),
                text='\n\n',
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=1, character=0),
                    end=Position(line=1, character=0)
                ),
                text='\n',
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=2, character=0),
                    end=Position(line=2, character=0)
                ),
                text='A',
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=2, character=1),
                    end=Position(line=2, character=1)
                ),
                text='s',
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=2, character=2),
                    end=Position(line=2, character=2)
                ),
                text='d',
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=2, character=3),
                    end=Position(line=2, character=3)
                ),
                text='f',
            ),
        ],
        'This is a sentence.\n'
        '\n'
        'Asdf\n',
        None,
        None,
    ),
    (
        # Based on a bug in nvim
        'This is paragraph one.\n'
        '\n'
        'Sentence one. Sentence two.\n'
        '\n'
        'Sentence three.\n'
        '\n'
        '# Header\n',
        [
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=2, character=13),
                    end=Position(line=2, character=27),
                ),
                text=''
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=3, character=0),
                    end=Position(line=4, character=0),
                ),
                text=''
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=3, character=0),
                    end=Position(line=3, character=15),
                ),
                text=''
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=2, character=13),
                    end=Position(line=2, character=13),
                ),
                text=''
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=3, character=0),
                    end=Position(line=4, character=0),
                ),
                text=''
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=2, character=13),
                    end=Position(line=2, character=13),
                ),
                text=' Sentence two.\n\nSentence three.'
            ),
        ],
        'This is paragraph one.\n'
        '\n'
        'Sentence one. Sentence two.\n'
        '\n'
        'Sentence three.\n'
        '\n'
        'Header\n',
        None,
        None,
    ),
    (
        'This is paragraph one.\n'
        '\n'
        '\n'
        'Sentence one. Sentence two.\n',
        [
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=1, character=0),
                    end=Position(line=2, character=0),
                ),
                text='\n\n',
            ),
        ],
        'This is paragraph one.\n'
        '\n'
        'Sentence one. Sentence two.\n',
        None,
        None,
    ),
    (
        'This is paragraph one.\n'
        '\n'
        '\n'
        '\n'
        'Sentence one. Sentence two.\n',
        [
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=2, character=0),
                    end=Position(line=2, character=0)
                ),
                text='A'
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=2, character=1),
                    end=Position(line=2, character=1)
                ),
                text='s'
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=2, character=2),
                    end=Position(line=2, character=2)
                ),
                text='d'
            ),
        ],
        'This is paragraph one.\n'
        '\n'
        'Asd\n'
        '\n'
        'Sentence one. Sentence two.\n',
        None,
        None,
    ),
    (
        'This is paragraph one.\n'
        '\n'
        'Sentence one. Sentence two.\n',
        [
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=0, character=22),
                    end=Position(line=0, character=22)
                ),
                text=' '
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=0, character=22),
                    end=Position(line=0, character=23)
                ),
                text='\n'
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=1, character=0),
                    end=Position(line=1, character=0)
                ),
                text='A'
            ),
        ],
        'This is paragraph one. A\n'
        '\n'
        'Sentence one. Sentence two.\n',
        None,
        None,
    ),
    (
        'This is a sentence.\n'
        '\n'
        'Header\n'
        'This is a sentence.\n',
        [
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=2, character=0),
                    end=Position(line=2, character=0)
                ),
                text='#'
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=2, character=1),
                    end=Position(line=2, character=1)
                ),
                text=' '
            ),
        ],
        'This is a sentence.\n'
        '\n'
        'Header\n'
        '\n'
        'This is a sentence.\n',
        None,
        None,
    ),
    (
        'Header\n'
        'This is a sentence.\n',
        [
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=0, character=0),
                    end=Position(line=0, character=0)
                ),
                text='#'
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=0, character=1),
                    end=Position(line=0, character=1)
                ),
                text=' '
            ),
        ],
        'Header\n'
        '\n'
        'This is a sentence.\n',
        None,
        None,
    ),
    (
        'This is a sentence.\n'
        '\n'
        '# Header\n'
        'This is a sentence.\n',
        [
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=2, character=1),
                    end=Position(line=2, character=2)
                ),
                text=''
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=2, character=0),
                    end=Position(line=2, character=1)
                ),
                text=''
            ),
        ],
        'This is a sentence.\n'
        '\n'
        'Header This is a sentence.\n',
        None,
        None,
    ),
    (
        'This is a sentence.\n',
        [
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=0, character=0),
                    end=Position(line=1, character=0)
                ),
                text=''
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=0, character=0),
                    end=Position(line=0, character=0)
                ),
                text='This is a sentence.'
            ),
        ],
        'This is a sentence.\n',
        None,
        None,
    ),
    (
        '* This is point one.\n'
        '* This is point two.\n',
        [
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=0, character=0),
                    end=Position(line=0, character=0)
                ),
                text='* This is point one.\n'
            ),
        ],
        'This is point one.\n'
        '\n'
        'This is point one.\n'
        '\n'
        'This is point two.\n',
        None,
        None,
    ),
    (
        'This is a sentence.\n'
        'A\n',
        [
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=1, character=1),
                    end=Position(line=1, character=1)
                ),
                text='B'
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=1, character=2),
                    end=Position(line=1, character=2)
                ),
                text=' '
            ),
        ],
        'This is a sentence. AB\n',
        None,
        None,
    ),
    (
        'This is a sentence.\n'
        'A\n',
        [
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=1, character=1),
                    end=Position(line=1, character=1)
                ),
                text=' '
            ),
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=1, character=2),
                    end=Position(line=1, character=2)
                ),
                text=' '
            ),
        ],
        'This is a sentence. A\n',
        None,
        None,
    ),
    (
        'This is a sentence.\n'
        '\n'
        '   This will be an unparsed part.\n'
        '\n'
        'This is a sentence.\n',
        [
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=2, character=0),
                    end=Position(line=2, character=0)
                ),
                text=' '
            ),
        ],
        'This is a sentence.\n'
        '\n'
        'This is a sentence.\n',
        None,
        None,
    ),
    (
        'This is a sentence.\n'
        '\n'
        '    This will be a parsed part.\n'
        '\n'
        'This is a sentence.\n',
        [
            TextDocumentContentChangeEvent_Type1(
                range=Range(
                    start=Position(line=2, character=0),
                    end=Position(line=2, character=1)
                ),
                text=''
            ),
        ],
        'This is a sentence.\n'
        '\n'
        'This will be a parsed part.\n'
        '\n'
        'This is a sentence.\n',
        None,
        None,
    ),
])
def test_edits(content, changes, exp, offset_test, position_test):
    doc = MarkDownDocument('DUMMY_URL', content)
    doc.cleaned_source
    for change in changes:
        doc.apply_change(change)
    assert doc.cleaned_source == exp

    if offset_test is not None:
        offset = offset_test[0]
        if offset < 0:
            offset = len(exp) + offset
        assert doc.text_at_offset(offset, len(offset_test[1]), True) == offset_test[1]
        if len(offset_test) > 2:
            assert doc.range_at_offset(offset, len(offset_test[1]), True) == offset_test[2]
    if position_test is not None:
        offset = doc.offset_at_position(position_test[0], True)
        assert doc.text_at_offset(offset, len(position_test[1]), True) == position_test[1]
