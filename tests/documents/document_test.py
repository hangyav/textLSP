import pytest

from lsprotocol.types import (
    Position,
    Range,
    TextDocumentContentChangeEvent_Type1,
)

from textLSP.types import Interval
from textLSP.documents.document import BaseDocument, ChangeTracker


@pytest.mark.parametrize('content,position,exp', [
    (
        '1. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '2. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '3. This is a sentence. Another sentence in a paragraph.\n',
        Position(
            line=0,
            character=5,
        ),
        '1. This is a sentence. Another sentence in a paragraph.\n',
    ),
    (
        '1. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '2. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '3. This is a sentence. Another sentence in a paragraph.\n',
        Position(
            line=2,
            character=0,
        ),
        '2. This is a sentence. Another sentence in a paragraph.\n',
    ),
    (
        '1. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '2. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '3. This is a sentence. Another sentence in a paragraph.\n',
        Position(
            line=4,
            character=54,
        ),
        '3. This is a sentence. Another sentence in a paragraph.\n',
    ),
    (
        '1. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '2. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '3. This is a sentence. Another sentence in a paragraph.\n',
        Position(
            line=1,
            character=0,
        ),
        '\n',
    ),
    (
        '1. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '2. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '3. This is a sentence. Another sentence in a paragraph.\n',
        Position(
            line=0,
            character=55,
        ),
        '1. This is a sentence. Another sentence in a paragraph.\n',
    ),
])
def test_get_paragraph_at_position(content, position, exp):
    doc = BaseDocument('DUMMY_URL', content)
    pos = doc.paragraph_at_position(position)
    par = doc.source[pos.start:pos.start+pos.length]

    assert par == exp


@pytest.mark.parametrize('content,range,exp', [
    (
        '1. This is a sentence. Another sentence in a paragraph.\n\n'
        '2. This is a sentence. Another sentence in a paragraph.\n\n'
        '3. This is a sentence. Another sentence in a paragraph.\n',
        Range(
            start=Position(
                line=0,
                character=5,
            ),
            end=Position(
                line=2,
                character=5,
            ),
        ),
        [
            '1. This is a sentence. Another sentence in a paragraph.\n',
            '\n',
            '2. This is a sentence. Another sentence in a paragraph.\n',
        ],
    ),
])
def test_get_paragraphs_at_range(content, range, exp):
    doc = BaseDocument('DUMMY_URL', content)
    par_lst = doc.paragraphs_at_range(range)
    par_lst = [
        doc.source[pos.start:pos.start+pos.length]
        for pos in par_lst
    ]

    assert par_lst == exp


@pytest.mark.parametrize('content,interval,exp', [
    (
        '1. This is a sentence. Another sentence in a paragraph.\n\n'
        '2. This is a sentence. Another sentence in a paragraph.\n\n'
        '3. This is a sentence. Another sentence in a paragraph.\n',
        Interval(0, 170),  # full document
        [
            '1. This is a sentence. Another sentence in a paragraph.\n',
            '\n',
            '2. This is a sentence. Another sentence in a paragraph.\n',
            '\n',
            '3. This is a sentence. Another sentence in a paragraph.\n',
        ],
    ),
])
def test_get_paragraphs_at_offset(content, interval, exp):
    doc = BaseDocument('DUMMY_URL', content)
    par_lst = doc.paragraphs_at_offset(interval.start, interval.length)
    par_lst = [
        doc.source[pos.start:pos.start+pos.length]
        for pos in par_lst
    ]

    assert par_lst == exp


@pytest.mark.parametrize('content,offset,length,exp', [
    (
        '1. This is a sentence. Another sentence in a paragraph.\n'
        '2. This is a sentence. Another sentence in a paragraph.\n'
        '3. This is a sentence. Another sentence in a paragraph.\n',
        0, 0,
        '1. ',
    ),
    (
        '1. This is a sentence. Another sentence in a paragraph.\n'
        '2. This is a sentence. Another sentence in a paragraph.\n'
        '3. This is a sentence. Another sentence in a paragraph.\n',
        0, 3,
        '1. ',
    ),
    (
        '1. This is a sentence. Another sentence in a paragraph.\n'
        '2. This is a sentence. Another sentence in a paragraph.\n'
        '3. This is a sentence. Another sentence in a paragraph.\n',
        0, 4,
        '1. This is a sentence. ',
    ),
    (
        '1. This is a sentence. Another sentence in a paragraph.\n'
        '2. This is a sentence. Another sentence in a paragraph.\n'
        '3. This is a sentence. Another sentence in a paragraph.\n',
        22, 0,
        'This is a sentence. ',
    ),
    (
        '1. This is a sentence. Another sentence in a paragraph.\n'
        '2. This is a sentence. Another sentence in a paragraph.\n'
        '3. This is a sentence. Another sentence in a paragraph.\n',
        23, 0,
        'Another sentence in a paragraph.\n',
    ),
    (
        '1. This is a sentence. Another sentence in a paragraph.\n'
        '2. This is a sentence. Another sentence in a paragraph.\n'
        '3. This is a sentence. Another sentence in a paragraph.\n',
        167, 0,
        'Another sentence in a paragraph.\n',
    ),
])
def test_get_sentence_at_offset(content, offset, length, exp):
    doc = BaseDocument('DUMMY_URL', content)
    pos = doc.sentence_at_offset(offset, length)
    par = doc.source[pos.start:pos.start+pos.length]

    assert par == exp


@pytest.mark.parametrize('content,edits,exp', [
    (
        '1. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '2. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '3. This is a sentence. Another sentence in a paragraph.\n',
        [
            TextDocumentContentChangeEvent_Type1(
                # delete 'o' from Another
                range=Range(
                    start=Position(
                        line=0,
                        character=25,
                    ),
                    end=Position(
                        line=0,
                        character=26,
                    ),
                ),
                text='',
            ),
        ],
        [
            Interval(24, 1),
        ],
    ),
    (
        '1. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '2. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '3. This is a sentence. Another sentence in a paragraph.\n',
        [
            TextDocumentContentChangeEvent_Type1(
                # delete 'o' from Another
                range=Range(
                    start=Position(
                        line=0,
                        character=25,
                    ),
                    end=Position(
                        line=0,
                        character=26,
                    ),
                ),
                text='',
            ),
            TextDocumentContentChangeEvent_Type1(
                # insert 'o'
                range=Range(
                    start=Position(
                        line=0,
                        character=25,
                    ),
                    end=Position(
                        line=0,
                        character=25,
                    ),
                ),
                text='o',
            ),
        ],
        [
            Interval(24, 1),
            Interval(25, 1),
        ],
    ),
    (
        '1. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '2. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '3. This is a sentence. Another sentence in a paragraph.\n',
        [
            TextDocumentContentChangeEvent_Type1(
                # delete last character
                range=Range(
                    start=Position(
                        line=4,
                        character=54,
                    ),
                    end=Position(
                        line=4,
                        character=55,
                    ),
                ),
                text='',
            ),
            TextDocumentContentChangeEvent_Type1(
                # put it back
                range=Range(
                    start=Position(
                        line=4,
                        character=54,
                    ),
                    end=Position(
                        line=4,
                        character=54,
                    ),
                ),
                text='.',
            ),
        ],
        [
            Interval(167, 1),
            Interval(168, 1),
        ],
    ),
    (
        '1. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '2. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '3. This is a sentence. Another sentence in a paragraph.\n',
        [
            TextDocumentContentChangeEvent_Type1(
                # add character at the end
                range=Range(
                    start=Position(
                        line=4,
                        character=55,
                    ),
                    end=Position(
                        line=4,
                        character=55,
                    ),
                ),
                text='c',
            ),
        ],
        [
            Interval(169, 1),
        ],
    ),
    (
        '1. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '2. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '3. This is a sentence. Another sentence in a paragraph.\n'
        '\n',
        [
            TextDocumentContentChangeEvent_Type1(
                # remove line at the end
                range=Range(
                    start=Position(
                        line=5,
                        character=0,
                    ),
                    end=Position(
                        line=6,
                        character=0,
                    ),
                ),
                text='',
            ),
        ],
        [
            Interval(169, 1),
        ],
    ),
    (
        '1. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '2. This is a sentence. Another sentence in a paragraph.\n'
        '\n'
        '3. This is a sentence. Another sentence in a paragraph.\n',
        [
            TextDocumentContentChangeEvent_Type1(
                # add character at the end
                range=Range(
                    start=Position(
                        line=4,
                        character=55,
                    ),
                    end=Position(
                        line=4,
                        character=55,
                    ),
                ),
                text='a',
            ),
            TextDocumentContentChangeEvent_Type1(
                # add character at the end
                range=Range(
                    start=Position(
                        line=4,
                        character=56,
                    ),
                    end=Position(
                        line=4,
                        character=56,
                    ),
                ),
                text='s',
            ),
            TextDocumentContentChangeEvent_Type1(
                # add character at the end
                range=Range(
                    start=Position(
                        line=4,
                        character=57,
                    ),
                    end=Position(
                        line=4,
                        character=57,
                    ),
                ),
                text='d',
            ),
        ],
        [
            Interval(169, 1),
            Interval(170, 1),
            Interval(171, 1),
        ],
    ),
])
def test_updates(content, edits, exp):
    doc = BaseDocument('DUMMY_URL', content)
    tracker = ChangeTracker(doc, True)

    for edit in edits:
        tracker.update_document(edit)

    assert tracker.get_changes() == exp
