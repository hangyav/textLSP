import pytest

from textLSP.analysers.hf_completion import HFCompletionAnalyser


@pytest.fixture
def analyser():
    return HFCompletionAnalyser(
        None,
        {},
        'hf_checker',
    )


def test_simple(analyser):
    # test initialization
    pass
