import pytest

from lsprotocol.types import Position, Range
from textLSP.documents.latex import LatexDocument


@pytest.mark.parametrize('src,clean', [
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


@pytest.mark.parametrize('src,offset,exp', [
    (
        '\\section{Introduction}\n'
        '\n'
        'This is a \\textbf{sentence}.',
        (0, 12),
        'Introduction',
    ),
    (
        '\\section{Introduction}\n'
        '\n'
        'This is a \\textbf{sentence}.',
        (24, 8),
        'sentence',
    ),
])
def test_highlight(src, offset, exp):
    doc = LatexDocument(
        'tmp.tex',
        src,
    )

    pos_range = doc.range_at_offset(offset[0], offset[1], True)

    lines = src.splitlines(True)
    if pos_range.start.line == pos_range.end.line:
        res = lines[pos_range.start.line][pos_range.start.character:pos_range.end.character]
    else:
        res = lines[pos_range.start.line][pos_range.start.character:]
        res += ''.join([lines[idx] for idx in range(pos_range.start.line+1, pos_range.end.line)])
        res += lines[pos_range.end.line][:pos_range.end.character]

    assert res == exp


@pytest.mark.parametrize('content,position,exp', [
    (
        '\\documentclass[11pt]{article}\n'
        '\\begin{document}\n'
        '\n'
        '\\section{Introduction}\n'
        '\n'
        'This is a sentence.\n'
        '\n'
        '\\end{document}',
        Position(
            line=3,
            character=19,
        ),
        'Introduction',
    ),
    (
        '\\documentclass[11pt]{article}\n'
        '\\begin{document}\n'
        '\n'
        '\\section{Introduction}\n'
        '\n'
        'This is a sentence.\n'
        '\n'
        '\\end{document}',
        Position(
            line=3,
            character=9,  # first char
        ),
        'Introduction',
    ),
    (
        '\\documentclass[11pt]{article}\n'
        '\\begin{document}\n'
        '\n'
        '\\section{Introduction}\n'
        '\n'
        'This is a sentence.\n'
        '\n'
        '\\end{document}',
        Position(
            line=3,
            character=20,  # last char
        ),
        'Introduction',
    ),
    (
        '\\documentclass[11pt]{article}\n'
        '\\begin{document}\n'
        '\n'
        '\\section{Introduction}\n'
        '\n'
        'This is a sentence.\n'
        '\n'
        '\\end{document}',
        Position(
            line=4,
            character=0,
        ),
        '\n',
    ),
    (
        '\\documentclass[11pt]{article}\n'
        '\\begin{document}\n'
        '\n'
        '\\section{Introduction}\n'
        '\n'
        'This is a sentence.\n'
        '\n'
        '\\end{document}',
        Position(
            line=5,
            character=0,
        ),
        'This is a sentence.',
    ),
])
def test_get_paragraph(content, position, exp):
    doc = LatexDocument('DUMMY_URL', content)
    pos = doc.paragraph_at_position(position, True)
    par = doc.cleaned_source[pos.start:pos.start+pos.length]

    assert par == exp


@pytest.mark.parametrize('content,range,exp', [
    (
        '\\documentclass[11pt]{article}\n'
        '\\begin{document}\n'
        '\n'
        '\\section{Introduction}\n'
        '\n'
        'This is a sentence.\n'
        '\n'
        '\\end{document}',
        Range(
            start=Position(
                line=3,
                character=13,
            ),
            end=Position(
                line=5,
                character=5,
            ),
        ),
        [
            'Introduction',
            '\n',
            '\n',
            'This is a sentence.',
        ],
    ),
])
def test_get_paragraphs_at_range(content, range, exp):
    doc = LatexDocument('DUMMY_URL', content)
    par_lst = doc.paragraphs_at_range(range, True)
    par_lst = [
        doc.cleaned_source[pos.start:pos.start+pos.length]
        for pos in par_lst
    ]

    assert par_lst == exp
