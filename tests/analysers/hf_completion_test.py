import pytest

from textLSP.analysers.hf_completion import HFCompletionAnalyser


@pytest.fixture
def analyser():
    return HFCompletionAnalyser(
        None,
        {},
        'hf_completion',
    )


def test_simple(analyser):
    text = 'The next word should be '
    analyser._get_text_completions(text, len(text)-1)
