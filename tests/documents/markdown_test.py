import pytest

from textLSP.documents.markdown.markdown import MarkDownDocument


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
