import pytest

from textLSP.documents.org import OrgDocument


@pytest.mark.parametrize('src,clean', [
    (
        '** DONE Task 1                            :TAG:\n'
        '  SCHEDULED: <2023-01-27 Fri> CLOSED: [2023-01-27 Fri 13:01]\n'
        '  - Level 1 list:\n'
        '    - Level 2 list 1\n'
        '    - Level 2 list 2',
        #
        'Task 1\n'
        'Level 1 list:\n'
        'Level 2 list 1\n'
        'Level 2 list 2\n'
    ),
    (
        '** Task 1\n'
        '  This is a paragraph.\n'
        '** Task 2\n'
        '  This is a paragraph.\n',
        #
        'Task 1\n'
        'This is a paragraph.\n'
        '\n'
        'Task 2\n'
        'This is a paragraph.\n'
    ),
    (
        '** Task 1\n'
        '  This is a paragraph.\n'
        '  This is another sentence in it.',
        #
        'Task 1\n'
        'This is a paragraph. This is another sentence in it.\n'
    ),
    (
        '** Task 1\n'
        '  This is a paragraph.\n'
        '\n'
        '  This is another paragraph.',
        #
        'Task 1\n'
        'This is a paragraph.\n'
        '\n'
        'This is another paragraph.\n'
    ),
])
def test_clean(src, clean):
    doc = OrgDocument(
        'tmp.org',
        src,
        config={OrgDocument.CONFIGURATION_TODO_KEYWORDS: {'DONE'}}
    )

    assert doc.cleaned_source == clean
