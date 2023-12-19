import pytest

from textLSP.analysers.openai import OpenAIAnalyser
from openai import AuthenticationError


@pytest.fixture
def analyser():
    return OpenAIAnalyser(
        None,
        {OpenAIAnalyser.CONFIGURATION_API_KEY: 'DUMMY_KEY'},
        'openai',
    )


def test_edit(analyser):
    try:
        analyser._edit('This is as santance.')
    except AuthenticationError:
        pass


def test_generate(analyser):
    try:
        analyser._generate('Write me a sentence:')
    except AuthenticationError:
        pass
