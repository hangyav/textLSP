from .document import TreeSitterDocument


class LatexDocument(TreeSitterDocument):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        TreeSitterDocument.build_library(
            'latex',
            'https://github.com/latex-lsp/tree-sitter-latex',
        )

    def _iterate_text_nodes(self):
        # TODO yield something
        raise NotImplementedError()
