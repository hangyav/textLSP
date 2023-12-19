import pytest

try:
    # gramformer is not on pypi thus not installed automatically
    from gramformer import Gramformer
except ModuleNotFoundError:
    import sys
    import subprocess
    subprocess.check_call([
        sys.executable,
        "-m",
        "pip",
        "install",
        'git+https://github.com/PrithivirajDamodaran/Gramformer.git'
    ])

from textLSP.documents.document import BaseDocument
from textLSP.analysers.gramformer import GramformerAnalyser


@pytest.fixture
def analyser():
    return GramformerAnalyser(
        None,
        {},
        'gramformer',
    )


def test_analyse(analyser):
    doc = BaseDocument(
        'tmp.txt',
        'This is a santance. And another.',
        config={},
        version=0
    )
    analyser._analyse_sentences(doc.cleaned_source, doc)
