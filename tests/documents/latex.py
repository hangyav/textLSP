import pytest

from textLSP.documents.latex import LatexDocument


def test_latex_clean1():
    source = """\\documentclass[11pt]{article}
    \\begin{document}

    \\section{Introduction}

    This is a sentence.

    \\end{document}"""

    expected = "11pt\ndocument\n\nIntroduction\n\nThis is a sentence.\n\ndocument"

    doc = LatexDocument(
        'tmp.tex',
        source,
    )

    assert doc.cleaned_source == expected
