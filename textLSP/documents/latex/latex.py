from tree_sitter import Tree, Node

from ..document import TreeSitterDocument


class LatexDocument(TreeSitterDocument):

    def __init__(self, *args, **kwargs):
        super().__init__(
            'latex',
            'https://github.com/latex-lsp/tree-sitter-latex',
            *args,
            **kwargs,
        )

    def _is_valid_node(self, node: Node) -> bool:
        # TODO
        return node.type == 'word' and node.parent.type == 'text'

    def _iterate_text_nodes(self, tree: Tree) -> Node:
        cursor = tree.walk()

        reached_root = False
        while not reached_root:
            if self._is_valid_node(cursor.node):
                yield cursor.node
                if cursor.goto_next_sibling():
                    # False if no sibling
                    continue
                reached_root = LatexDocument.retrace(cursor)

            if cursor.goto_first_child():
                # False if no children
                continue

            if cursor.goto_next_sibling():
                # False if no sibling
                continue

            reached_root = LatexDocument.retrace(cursor)

    @staticmethod
    def retrace(cursor) -> bool:
        """
        return True if reached root
        """
        while True:
            if not cursor.goto_parent():
                return True

            if cursor.goto_next_sibling():
                return False
