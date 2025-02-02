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
    with pytest.raises(AuthenticationError):
        analyser._edit('This is as santance.')


def test_generate(analyser):
    with pytest.raises(AuthenticationError):
        analyser._generate('Write me a sentence:')
