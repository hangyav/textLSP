import pytest

from textLSP.documents.txt import TxtDocument


@pytest.mark.parametrize('src,clean', [
    (
        'This is a sentence.',
        #
        'This is a sentence.',
    ),
    (
        'This is a sentence.\n',
        #
        'This is a sentence.\n',
    ),
    (
        '\n\nThis is a sentence.',
        #
        '\n\nThis is a sentence.',
    ),
    (
        'This is a sentence.\n'
        'This is a sentence.',
        #
        'This is a sentence.'
        ' '
        'This is a sentence.',
    ),
    (
        'This is a sentence.\n'
        '\n'
        'This is a sentence.',
        #
        'This is a sentence.\n'
        '\n'
        'This is a sentence.',
    ),
])
def test_clean(src, clean):
    doc = TxtDocument(
        'tmp.txt',
        src,
    )

    assert doc.cleaned_source == clean


@pytest.mark.parametrize('src,offset,exp', [
    (
        'This is a sentence.',
        # (offset, length)
        (0, 4),
        'This',
    ),
    (
        'This is a sentence.',
        # (offset, length)
        (5, 4),
        'is a',
    ),
    (
        'This is a sentence.\n'
        '\n'
        'That is a file.',
        # (offset, length)
        (31, 4),
        'file',
    ),
])
def test_highlight(src, offset, exp):
    doc = TxtDocument(
        'tmp.txt',
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
