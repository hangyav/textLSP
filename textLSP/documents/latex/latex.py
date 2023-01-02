from typing import Generator, List, Optional
from tree_sitter import Tree, Node, TreeCursor

from ..document import TreeSitterDocument, TextNode


class LatexDocument(TreeSitterDocument):
    TEXT = 'text'
    WORD = 'word'
    SECTION = 'section'
    SUBSECTION = 'subsection'
    PARAGRAPH = 'paragraph'
    CURLY_GROUP = 'curly_group'
    ENUM_ITEM = 'enum_item'
    GENERIC_ENVIRONMENT = 'generic_environment'

    TEXT_ROOTS = {
        SECTION,
        SUBSECTION,
        PARAGRAPH,
        CURLY_GROUP,
        ENUM_ITEM,
        GENERIC_ENVIRONMENT,
    }

    NEWLINE_BEFORE_AFTER_CURLY_PARENT = {
        SECTION,
        SUBSECTION,
        PARAGRAPH,
    }

    NEWLINE_BEFORE_AFTER = {
        ENUM_ITEM,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(
            'latex',
            'https://github.com/latex-lsp/tree-sitter-latex',
            *args,
            **kwargs,
        )

    def _is_valid_node(self, node: Node) -> bool:
        parent = node.parent
        if parent is None:
            return False
        pparent = parent.parent
        if pparent is None:
            return False
        return (node.type == LatexDocument.WORD
                and parent.type == LatexDocument.TEXT
                and pparent.type in LatexDocument.TEXT_ROOTS)

    def _iterate_text_nodes(self, tree: Tree) -> Generator[TextNode, None, None]:
        cursor = tree.walk()
        lines = tree.text.decode('utf-8').split('\n')
        yield from self._walk_ts_tree(cursor, lines)

    def _walk_ts_tree(
            self,
            cursor: TreeCursor,
            lines: List[str],
            last_sent: Optional[TextNode] = None) -> Generator[TextNode, None, None]:
        if last_sent is not None:
            for node in self._get_new_lines(
                self._needs_newline_before(cursor.node, lines, last_sent),
                cursor.node.end_point,
            ):
                yield node
                last_sent = node

        is_valid = False
        if self._is_valid_node(cursor.node):
            is_valid = True

            if last_sent is not None and cursor.node.start_point[0] - last_sent.end_point[0] > 1:
                if any(line == '' for line in lines[last_sent.end_point[0]+1:cursor.node.start_point[0]]):
                    yield TextNode(
                        text='\n',
                        start_point=(last_sent.end_point[0], last_sent.end_point[1]+1),
                        end_point=(last_sent.end_point[0], last_sent.end_point[1]+2),
                    )
                    last_sent = TextNode(
                        text='\n',
                        start_point=(last_sent.end_point[0]+1, 0),
                        end_point=(last_sent.end_point[0]+1, 1),
                    )
                    yield last_sent

            if self._needs_space_before(cursor.node, lines, last_sent):
                sp = cursor.node.start_point
                if sp[1] > 0:
                    yield TextNode.space(
                        start_point=(sp[0], sp[1]-1),
                        end_point=sp
                    )
                else:
                    yield TextNode.space(
                        start_point=(last_sent.end_point[0], last_sent.end_point[1]+1),
                        end_point=(last_sent.end_point[0], last_sent.end_point[1]+2),
                    )
            last_sent = TextNode.from_ts_node(cursor.node)
            yield last_sent

        if not is_valid and cursor.goto_first_child():
            for node in self._walk_ts_tree(cursor, lines, last_sent):
                yield node
                last_sent = node
            cursor.goto_parent()

        for node in self._get_new_lines(
            self._needs_newline_after(cursor.node, lines, last_sent),
            cursor.node.end_point,
        ):
            yield node
            last_sent = node

        while cursor.goto_next_sibling():
            for node in self._walk_ts_tree(cursor, lines, last_sent):
                yield node
                last_sent = node

    def _needs_newline_before(self, node, lines, last_sent) -> int:
        return self._needs_newline_beforeafter(node, lines, last_sent)

    def _needs_newline_after(self, node, lines, last_sent) -> int:
        return self._needs_newline_beforeafter(node, lines, last_sent)

    def _needs_newline_beforeafter(self, node, lines, last_sent) -> int:
        if (node.type == LatexDocument.CURLY_GROUP
                and node.parent.type in LatexDocument.NEWLINE_BEFORE_AFTER_CURLY_PARENT):
            return 2
        if node.type in LatexDocument.NEWLINE_BEFORE_AFTER:
            return 2
        return 0

    def _get_new_lines(self, num, location):
        return (
            TextNode.new_line(
                start_point=(
                    location[0]+i,
                    location[1]+1 if i == 0 else 0
                ),
                end_point=(
                    location[0]+i,
                    location[1]+2 if i == 0 else 1
                ),
            )
            for i in range(num)
        )

    def _needs_space_before(self, node, lines, last_sent) -> bool:
        if last_sent is None:
            return False
        if node.start_point[0] == last_sent.end_point[0]:
            return ' ' in lines[node.start_point[0]][last_sent.end_point[1]:node.start_point[1]]
        return last_sent.text != '\n'
