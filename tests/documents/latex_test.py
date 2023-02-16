import pytest

from lsprotocol.types import (
    Position,
    Range,
    TextDocumentContentChangeEvent_Type1
)
from textLSP.types import Interval
from textLSP.documents.document import ChangeTracker
from textLSP.documents.latex import LatexDocument


@pytest.mark.parametrize('src,clean', [
    (
        '\\section{Introduction}\n'
        '\n'
        'This is a \\textbf{sentence}.',
        'Introduction\n'
        '\n'
        'This is a sentence.\n'
    ),
    (
        '\\paragraph{Introduction}\n'
        '\n'
        'This is a \\textbf{sentence}.',
        'Introduction\n'
        '\n'
        'This is a sentence.\n'
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
    ),
    (
        '\\section{Introduction}\n'
        'This is a \n'
        '# comment\n'
        'sentence.\n',
        'Introduction\n'
        '\n'
        'This is a sentence.\n'
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
        'sentence.\n'
    ),
    (
        '\\section{Introduction}\n'
        'This is a, sentence with a comma.\n',
        'Introduction\n'
        '\n'
        'This is a, sentence with a comma.\n'
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
        'This is a sentence.\n'
    ),
    (
        '\\section{Introduction}\n'
        'This is the state-of-the-art sentence.\n',
        'Introduction\n'
        '\n'
        'This is the state-of-the-art sentence.\n',
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
        # (offset, length)
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
        res = lines[pos_range.start.line][pos_range.start.character:pos_range.end.character+1]
    else:
        res = lines[pos_range.start.line][pos_range.start.character:]
        res += ''.join([lines[idx] for idx in range(pos_range.start.line+1, pos_range.end.line)])
        res += lines[pos_range.end.line][:pos_range.end.character+1]

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
        'Introduction\n',
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
        'Introduction\n',
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
        'Introduction\n',
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
        'This is a sentence.\n',
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
        'This is a sentence.\n',
    ),
    (
        '\\documentclass[11pt]{article}\n'
        '\\begin{document}\n'
        '\n'
        '\\section{Intraduction}\\subsection{Subsection}\n'
        '\n'
        'This is a sentence.\n'
        'This is anather.\n'
        '\n'
        'This is \\textbf{bold}.\n'
        '\n'
        'One sentence\n'
        '% comment\n'
        '\n'
        'with words.\n'
        '\n'
        'This is a, sentence,\n'
        '\n'
        '\\paragraph{Porograph}\n'
        '\n'
        '\\begin{itemize}\n'
        '    \\item item 1\n'
        '    \\item itam 1\n'
        '\\end{itemize}\n'
        '\n'
        'Apple.\n'
        '\n'
        '\\end{document}\n',
        Position(
            line=17,
            character=12,
        ),
        'Porograph\n',
    ),
])
def test_get_paragraph_at_position(content, position, exp):
    doc = LatexDocument('DUMMY_URL', content)
    pos = doc.paragraph_at_position(position, True)
    if exp is None:
        assert pos is None
    else:
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
            'Introduction\n',
            '\n',
            'This is a sentence.\n',
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


@pytest.mark.parametrize('content,edits,exp', [
    # (
    #     '\\documentclass[11pt]{article}\n'
    #     '\\begin{document}\n'
    #     '\n'
    #     '\\section{Introduction}\n'
    #     '\n'
    #     'This is a sentence.\n'
    #     '\n'
    #     '\\end{document}',
    #     [
    #         TextDocumentContentChangeEvent_Type1(
    #             # delete 'o' from Introduction
    #             range=Range(
    #                 start=Position(
    #                     line=3,
    #                     character=13,
    #                 ),
    #                 end=Position(
    #                     line=3,
    #                     character=14,
    #                 ),
    #             ),
    #             text='',
    #         ),
    #     ],
    #     [
    #         Interval(3, 1),
    #     ],
    # ),
    # (
    #     '\\documentclass[11pt]{article}\n'
    #     '\\begin{document}\n'
    #     '\n'
    #     '\\section{Introduction}\n'
    #     '\n'
    #     'This is a sentence.\n'
    #     '\n'
    #     '\\end{document}',
    #     [
    #         TextDocumentContentChangeEvent_Type1(
    #             # delete 'o' from Introduction
    #             range=Range(
    #                 start=Position(
    #                     line=3,
    #                     character=13,
    #                 ),
    #                 end=Position(
    #                     line=3,
    #                     character=14,
    #                 ),
    #             ),
    #             text='',
    #         ),
    #         TextDocumentContentChangeEvent_Type1(
    #             # insert 'o'
    #             range=Range(
    #                 start=Position(
    #                     line=3,
    #                     character=13,
    #                 ),
    #                 end=Position(
    #                     line=3,
    #                     character=13,
    #                 ),
    #             ),
    #             text='o',
    #         ),
    #     ],
    #     [
    #         Interval(3, 1),
    #         Interval(4, 1),
    #     ],
    # ),
    # (
    #     '\\documentclass[11pt]{article}\n'
    #     '\\begin{document}\n'
    #     '\n'
    #     '\\section{Introduction}\n'
    #     '\n'
    #     'This is a sentence.\n'
    #     '\n'
    #     '\\end{document}',
    #     [
    #         TextDocumentContentChangeEvent_Type1(
    #             # delete last character
    #             range=Range(
    #                 start=Position(
    #                     line=5,
    #                     character=18,
    #                 ),
    #                 end=Position(
    #                     line=5,
    #                     character=19,
    #                 ),
    #             ),
    #             text='',
    #         ),
    #         TextDocumentContentChangeEvent_Type1(
    #             # put it back
    #             range=Range(
    #                 start=Position(
    #                     line=5,
    #                     character=18,
    #                 ),
    #                 end=Position(
    #                     line=5,
    #                     character=18,
    #                 ),
    #             ),
    #             text='.',
    #         ),
    #     ],
    #     [
    #         Interval(31, 1),
    #         Interval(32, 1),
    #     ],
    # ),
    # (
    #     '\\documentclass[11pt]{article}\n'
    #     '\\begin{document}\n'
    #     '\n'
    #     '\\section{Introduction}\n'
    #     '\n'
    #     'This is a sentence.\n'
    #     '\n'
    #     '\\end{document}',
    #     [
    #         TextDocumentContentChangeEvent_Type1(
    #             # add character at the end
    #             range=Range(
    #                 start=Position(
    #                     line=5,
    #                     character=19,
    #                 ),
    #                 end=Position(
    #                     line=5,
    #                     character=19,
    #                 ),
    #             ),
    #             text='c',
    #         ),
    #     ],
    #     [
    #         Interval(33, 1),
    #     ],
    # ),
    # (
    #     '\\documentclass[11pt]{article}\n'
    #     '\\begin{document}\n'
    #     '\n'
    #     '\\section{Introduction}\n'
    #     '\n'
    #     'This is a sentence.\n'
    #     '\n'
    #     '\\end{document}',
    #     [
    #         TextDocumentContentChangeEvent_Type1(
    #             # add character at the end
    #             range=Range(
    #                 start=Position(
    #                     line=5,
    #                     character=19,
    #                 ),
    #                 end=Position(
    #                     line=5,
    #                     character=19,
    #                 ),
    #             ),
    #             text='a',
    #         ),
    #         TextDocumentContentChangeEvent_Type1(
    #             # add character at the end
    #             range=Range(
    #                 start=Position(
    #                     line=5,
    #                     character=20,
    #                 ),
    #                 end=Position(
    #                     line=5,
    #                     character=20,
    #                 ),
    #             ),
    #             text='s',
    #         ),
    #         TextDocumentContentChangeEvent_Type1(
    #             # add character at the end
    #             range=Range(
    #                 start=Position(
    #                     line=5,
    #                     character=21,
    #                 ),
    #                 end=Position(
    #                     line=5,
    #                     character=21,
    #                 ),
    #             ),
    #             text='d',
    #         ),
    #     ],
    #     [
    #         Interval(33, 1),
    #         Interval(34, 1),
    #         Interval(35, 1),
    #     ],
    # ),
    (
        '\\documentclass[11pt]{article}\n'
        '\\begin{document}\n'
        '\n'
        '\\section{Introduction}\n'
        '\n'
        'This is a sentence \n'  # space at end
        '\n'
        '\\end{document}',
        [
            TextDocumentContentChangeEvent_Type1(
                # add character at the end
                range=Range(
                    start=Position(
                        line=5,
                        character=19,
                    ),
                    end=Position(
                        line=5,
                        character=19,
                    ),
                ),
                text='a',
            ),
            TextDocumentContentChangeEvent_Type1(
                # add character at the end
                range=Range(
                    start=Position(
                        line=5,
                        character=20,
                    ),
                    end=Position(
                        line=5,
                        character=20,
                    ),
                ),
                text='s',
            ),
            TextDocumentContentChangeEvent_Type1(
                # add character at the end
                range=Range(
                    start=Position(
                        line=5,
                        character=21,
                    ),
                    end=Position(
                        line=5,
                        character=21,
                    ),
                ),
                text='d',
            ),
        ],
        [
            Interval(33, 1),
            Interval(34, 1),
            Interval(35, 1),
        ],
    ),
])
def test_updates(content, edits, exp):
    doc = LatexDocument('DUMMY_URL', content)
    tracker = ChangeTracker(doc, True)

    for edit in edits:
        tracker.update_document(edit)

    assert tracker.get_changes() == exp
