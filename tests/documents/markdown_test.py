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
])
def test_clean(src, clean):
    doc = MarkDownDocument(
        'tmp.md',
        src,
        config={}
    )

    assert doc.cleaned_source == clean
