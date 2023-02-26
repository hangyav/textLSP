import pytest

from textLSP.analysers.hf_checker import HFCheckerAnalyser
from textLSP.documents.document import BaseDocument


@pytest.fixture
def analyser():
    return HFCheckerAnalyser(
        None,
        {HFCheckerAnalyser.CONFIGURATION_MIN_LENGTH: 40},
        'hf_checker',
    )


@pytest.mark.parametrize('doc,exp', [
    (
        BaseDocument(
            'DUMMY_URL',
            'This is a short sentence.',
            version=1,
        ),
        False,
    ),
    (
        BaseDocument(
            'DUMMY_URL',
            'This is a long enough sentence with an eror or tvo.',
            version=1,
        ),
        True,
    ),
])
def test_simple(doc, exp, analyser):
    res_diag, res_action = analyser._analyse_lines(doc.cleaned_source, doc)

    if exp:
        assert len(res_diag) > 0
        assert len(res_action) > 0
    else:
        assert len(res_diag) == 0
        assert len(res_action) == 0
