import pytest

from textLSP.analysers.ollama import OllamaAnalyser
from textLSP.types import ConfigurationError


def test_init():
    # there's no easy way to test this. So this is just a
    # placeholder for test coverage.
    with pytest.raises(ConfigurationError):
        return OllamaAnalyser(
            None,
            {OllamaAnalyser.CONFIGURATION_MODEL: 'DUMMY_MODEL'},
            'ollama',
        )
