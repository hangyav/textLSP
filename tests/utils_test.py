import pytest

from textLSP import utils


@pytest.mark.parametrize('src,exp,max,min', [
    (
        'This is a sentence of 47 characters. '
        'This is a sentence of 47 characters. '
        'This is a sentence of 47 characters.',
        [
            'This is a sentence of 47 characters. ',
            'This is a sentence of 47 characters. ',
            'This is a sentence of 47 characters.',
        ],
        47,
        0,
    ),
    (
        'This is a sentence of 47 characters. '
        'This is a sentence of 47 characters. '
        'This is a sentence of 47 characters.',
        [
            'This is a sentence of 47 characters. '
            'This is a sentence of 47 characters. '
            'This is a sentence of 47 characters.',
        ],
        3*47,
        0,
    ),
    (
        'This is a sentence of 47 characters.\n'
        'This is a sentence of 47 characters.\n'
        'This is a sentence of 47 characters.',
        [
            'This is a sentence of 47 characters.\n',
            'This is a sentence of 47 characters.\n',
            'This is a sentence of 47 characters.',
        ],
        47,
        0,
    ),
    (
        'This is a sentence of 47 characters. '
        'This is a sentence of 47 characters.',
        [
            'This is a sentence of 47 ',
            'characters. ',
            'This is a sentence of 47 ',
            'characters.',
        ],
        25,
        0,
    ),
    (
        'This is a sentence of 47 characters. '
        'This is a sentence of 47 characters.',
        [
            'This is a sentence of 47 ',
            'characters. This is a sen',
            'tence of 47 characters.',
        ],
        25,
        15,
    ),
    (
        'This is a. sentence of 48 characters. '
        'This is a. sentence of 48 characters. '
        'This is a sentence of 47 characters.',
        [
            'This is a. sentence of 48 characters. ',
            'This is a. sentence of 48 characters. ',
            'This is a sentence of 47 characters.',
        ],
        48,
        0,
    ),
])
def test_latex_clean(src, exp, max, min):
    res = list(utils.batch_text(src, utils.TEXT_PASSAGE_PATTERN, max, min))

    assert res == exp
