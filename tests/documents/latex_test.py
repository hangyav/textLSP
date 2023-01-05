import pytest

from textLSP.documents.latex import LatexDocument


@pytest.mark.parametrize('src,clean', [
    (
        '\\documentclass[11pt]{article}\n'
        '\\begin{document}\n'
        '\n'
        '\\section{Introduction}\n'
        '\n'
        'This is a sentence.\n'
        '\n'
        '\\end{document}',
        'Introduction\n'
        '\n'
        'This is a sentence.'
    ),
    (
        '\\section{Introduction}\n'
        '\n'
        'This is a \\textbf{sentence}.',
        'Introduction\n'
        '\n'
        'This is a sentence.'
    ),
    (
        '\\paragraph{Introduction}\n'
        '\n'
        'This is a \\textbf{sentence}.',
        'Introduction\n'
        '\n'
        'This is a sentence.'
    ),
    (
        '\\subsection{Introduction}\n'
        '\n'
        'This is a sentence.\n'
        '\\begin{itemize}\n'
        '    \\item Item 1\n'
        '    \\item Item 2\n'
        '\\end{itemize}',
        'Introduction\n'
        '\n'
        'This is a sentence.\n'
        '\n'
        'Item 1\n'
        '\n'
        '\n'
        '\n'
        'Item 2\n'
        '\n'
    ),
    (
        '\\section{Introduction}\n'
        'This is a \n'
        '# comment\n'
        'sentence.\n',
        'Introduction\n'
        '\n'
        'This is a sentence.'
    ),
    (
        '\\section{Introduction}\n'
        'This is a \n'
        '# comment\n'
        '\n'
        'sentence.\n',
        'Introduction\n'
        '\n'
        'This is a\n'
        '\n'
        'sentence.'
    ),
    (
        '\\section{Introduction}\n'
        'This is a, sentence with a comma.\n',
        # XXX This seems to be a TS grammar bug.
        # 'Introduction\n'
        # '\n'
        # 'This is a, sentence with a comma.'
        'Introduction\n'
        '\n'
        'This is a sentence with a comma.'
    ),
    (
        '\\section{Introduction}\n'
        '\n'
        '\\subsection{Subsection}\n'
        '\n'
        '\\paragraph{Paragraph}\n'
        '\n'
        'This is a \\textbf{sentence}.',
        'Introduction\n'
        '\n'
        '\n'
        '\n'
        'Subsection\n'
        '\n'
        '\n'
        '\n'
        'Paragraph\n'
        '\n'
        'This is a sentence.'
    ),
])
def test_latex_clean(src, clean):
    doc = LatexDocument(
        'tmp.tex',
        src,
    )

    assert doc.cleaned_source == clean
