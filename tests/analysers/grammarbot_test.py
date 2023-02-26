import pytest

from lsprotocol.types import Range, Position

from textLSP.analysers.grammarbot import GrammarBotAnalyser
from textLSP.documents.document import BaseDocument


@pytest.fixture
def analyser():
    return GrammarBotAnalyser(
        None,
        {GrammarBotAnalyser.CONFIGURATION_API_KEY: 'DUMMY_KEY'},
        'grammarbot',
    )


@pytest.mark.parametrize('doc,analyses,text_sections,exp', [
    (
        BaseDocument(
            'DUMMY_URL',
            'This is a sentence.'
        ),
        [
            {
                'offset': 0,
                'length': 5,
                'message': 'test',
                'rule': {'id': 'TEST'},
                'replacements': [],
            },
        ],
        None,
        [
            Range(
                start=Position(
                    line=0,
                    character=0
                ),
                end=Position(
                    line=0,
                    character=5
                ),

            ),
        ],
    ),
    (
        BaseDocument(
            'DUMMY_URL',
            'This is a paragraph.\n\n'
            'This is a paragraph.\n\n'
            'This is a paragraph.\n\n'
        ),
        [
            {
                'offset': 0,
                'length': 5,
                'message': 'test',
                'rule': {'id': 'TEST'},
                'replacements': [],
            },
        ],
        [
            (22, 21),  # second paragraph
        ],
        [
            Range(
                start=Position(
                    line=2,
                    character=0
                ),
                end=Position(
                    line=2,
                    character=5
                ),
            ),
        ],
    ),
    (
        BaseDocument(
            'DUMMY_URL',
            'This is a paragraph.\n\n'
            'This is a paragraph.\n\n'
            'This is a paragraph.\n\n'
        ),
        [
            {
                'offset': 5,
                'length': 2,
                'message': 'test',
                'rule': {'id': 'TEST'},
                'replacements': [],
            },
        ],
        [
            (22, 21),  # second paragraph
        ],
        [
            Range(
                start=Position(
                    line=2,
                    character=5
                ),
                end=Position(
                    line=2,
                    character=7
                ),
            ),
        ],
    ),
    (
        BaseDocument(
            'DUMMY_URL',
            'This is a paragraph.\n\n'
            'This is a paragraph.\n\n'
            'This is a paragraph.\n\n'
        ),
        [
            {
                'offset': 5,
                'length': 2,
                'message': 'test',
                'rule': {'id': 'TEST'},
                'replacements': [],
            },
            {
                'offset': 5 + len('This is a paragraph.\n'),
                'length': 2,
                'message': 'test',
                'rule': {'id': 'TEST'},
                'replacements': [],
            },
        ],
        [
            (0, len('This is a paragraph.\n')),
            # third paragraph
            (
                len('This is a paragraph.\n\nThis is a paragraph.\n\n'),
                2*len('This is a paragraph.\n')
            ),
        ],
        [
            Range(
                start=Position(
                    line=0,
                    character=5
                ),
                end=Position(
                    line=0,
                    character=7
                ),
            ),
            Range(
                start=Position(
                    line=4,
                    character=5
                ),
                end=Position(
                    line=4,
                    character=7
                ),
            ),
        ],
    ),
])
def test_analyses(doc, analyses, text_sections, exp, analyser):
    res_diag, res_action = analyser._handle_analyses(doc, analyses, text_sections)

    assert [diag.range for diag in res_diag] == exp
