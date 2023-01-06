import pytest

from lsprotocol.types import Position, Range

from textLSP.documents.document import BaseDocument


@pytest.mark.parametrize('content,position,exp', [
    (
        '1. This is a sentence. Another sentence in a paragraph.\n\n'
        '2. This is a sentence. Another sentence in a paragraph.\n\n'
        '3. This is a sentence. Another sentence in a paragraph.',
        Position(
            line=0,
            character=5,
        ),
        '1. This is a sentence. Another sentence in a paragraph.',
    ),
    (
        '1. This is a sentence. Another sentence in a paragraph.\n\n'
        '2. This is a sentence. Another sentence in a paragraph.\n\n'
        '3. This is a sentence. Another sentence in a paragraph.',
        Position(
            line=2,
            character=0,
        ),
        '2. This is a sentence. Another sentence in a paragraph.',
    ),
    (
        '1. This is a sentence. Another sentence in a paragraph.\n\n'
        '2. This is a sentence. Another sentence in a paragraph.\n\n'
        '3. This is a sentence. Another sentence in a paragraph.',
        Position(
            line=4,
            character=54,
        ),
        '3. This is a sentence. Another sentence in a paragraph.',
    ),
    (
        '1. This is a sentence. Another sentence in a paragraph.\n\n'
        '2. This is a sentence. Another sentence in a paragraph.\n\n'
        '3. This is a sentence. Another sentence in a paragraph.',
        Position(
            line=1,
            character=0,
        ),
        '\n',
    ),
])
def test_get_paragraph(content, position, exp):
    doc = BaseDocument('DUMMY_URL', content)
    pos = doc.paragraph_at_position(position)
    par = doc.source[pos.start:pos.start+pos.length]

    assert par == exp


@pytest.mark.parametrize('content,range,exp', [
    (
        '1. This is a sentence. Another sentence in a paragraph.\n\n'
        '2. This is a sentence. Another sentence in a paragraph.\n\n'
        '3. This is a sentence. Another sentence in a paragraph.',
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
            '1. This is a sentence. Another sentence in a paragraph.',
            '\n',
            '2. This is a sentence. Another sentence in a paragraph.',
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
