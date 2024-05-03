import pytest

from textLSP import utils, types


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
def test_batch_text(src, exp, max, min):
    res = list(utils.batch_text(src, types.TEXT_PASSAGE_PATTERN, max, min))

    assert res == exp


@pytest.mark.parametrize('s1,s2,exp', [
    (
        'This is a sentence of 47 characters. ',
        'This is a sentence of 48 characters. ',
        [
            types.TokenDiff(
                types.TokenDiff.REPLACE,
                '47',
                '48',
                22,
                2
            ),
        ],
    ),
    (
        'This is a sentence of 47 characters. ',
        'That is a sentence of 47 characters. ',
        [
            types.TokenDiff(
                types.TokenDiff.REPLACE,
                'This',
                'That',
                0,
                4
            ),
        ],
    ),
    (
        'This is a sentence of 47 characters. ',
        'This example is a sentence of 47 characters. ',
        [
            types.TokenDiff(
                types.TokenDiff.INSERT,
                '',
                ' example',
                4,
                0
            ),
        ],
    ),
    (
        'This example is a sentence of 47 characters. ',
        'This is a sentence of 47 characters. ',
        [
            types.TokenDiff(
                types.TokenDiff.DELETE,
                ' example',
                '',
                4,
                8
            ),
        ],
    ),
    (
        'This example is a sentence of 47 characters. ',
        'This is a good sentence of 48 characters. ',
        [
            types.TokenDiff(
                types.TokenDiff.DELETE,
                ' example',
                '',
                4,
                8
            ),
            types.TokenDiff(
                types.TokenDiff.INSERT,
                '',
                'good ',  # XXX: the position of space seems to be a bit inconsistent, before or after
                18,
                0
            ),
            types.TokenDiff(
                types.TokenDiff.REPLACE,
                '47',
                '48',
                30,
                2
            ),
        ],
    ),
    (
        'This is a sentence of 47 characters. ',
        'This is a sentence of 47 characters. ',
        [],
    ),
    (
        'This is a sentence.\n'
        '\n'
        'This is a new paragraph.\n',
        'This is a sentence.\n'
        '\n'
        'This is the new paragraph.\n',
        [
            types.TokenDiff(
                types.TokenDiff.REPLACE,
                'a',
                'the',
                29,
                1
            ),
        ],
    ),
    (
        'This is a sentence.\n'
        '\n'
        'This is a new paragraph.\n',
        'This is a sentence.\n'
        '\n'
        'That this is a new paragraph.\n',
        [
            types.TokenDiff(
                types.TokenDiff.REPLACE,
                'This',
                'That this',
                21,
                4
            ),
        ],
    ),
])
def test_token_diff(s1, s2, exp):
    res = types.TokenDiff.token_level_diff(s1, s2)

    assert res == exp
