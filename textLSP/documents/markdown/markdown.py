import os
from typing import Generator
import tempfile
from tree_sitter import Tree, Node, Language

from ..document import TreeSitterDocument, TextNode
from ...utils import git_clone


class MarkDownDocument(TreeSitterDocument):
    SUBFOLDER_MARKDOWN = 'tree-sitter-markdown'
    SUBFOLDER_MARKDOWN_INLINE = 'tree-sitter-markdown-inline'

    INLINE = 'inline'

    NODE_CONTENT = 'content'
    NODE_NEWLINE_AFTER_ONE = 'newline_after_one'
    NODE_NEWLINE_AFTER_TWO = 'newline_after_two'

    TEXT_ROOTS = {
        INLINE,
    }

    TEXT_ROOTS_WITH_ITEM = {
    }

    NEWLINE_AFTER_ONE = {
    }

    NEWLINE_AFTER_TWO = {
        INLINE,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(
            'markdown',
            'https://github.com/MDeiml/tree-sitter-markdown',
            *args,
            **kwargs,
        )
        self._query = self._build_query()

    @staticmethod
    def build_library(name, url) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            git_clone(url, tmpdir)
            Language.build_library(
                TreeSitterDocument.LIB_PATH_TEMPLATE.format(name),
                [os.path.join(tmpdir, MarkDownDocument.SUBFOLDER_MARKDOWN)]
            )

    def _build_query(self):
        query_str = ''

        for root in self.TEXT_ROOTS:
            query_str += f'({root}) @{self.NODE_CONTENT}\n'

        # for root in self.TEXT_ROOTS_WITH_ITEM:
        #     query_str += f'({root} (item ({self.EXPR}) @{self.NODE_CONTENT}))\n'

        for root in self.NEWLINE_AFTER_ONE:
            query_str += f'({root}) @{self.NODE_NEWLINE_AFTER_ONE}\n'

        for root in self.NEWLINE_AFTER_TWO:
            query_str += f'({root}) @{self.NODE_NEWLINE_AFTER_TWO}\n'

        return self._language.query(query_str)

    def _iterate_text_nodes(self, tree: Tree) -> Generator[TextNode, None, None]:
        lines = tree.text.decode('utf-8').split('\n')

        last_sent = None
        new_lines_after = list()

        for node in self._query.captures(tree.root_node):
            # Check if we need some newlines after previous elements
            while len(new_lines_after) > 0:
                if node[0].start_point > new_lines_after[0]:
                    if last_sent is not None:
                        for nl in TextNode.get_new_lines(1, last_sent.end_point):
                            last_sent = nl
                            yield nl
                    new_lines_after.pop(0)
                else:
                    break

            if node[1] == self.NODE_CONTENT:
                # handle spaces
                if self._needs_space_before(node[0], lines, last_sent):
                    sp = node[0].start_point
                    if sp[1] > 0:
                        yield TextNode.space(
                            start_point=(sp[0], sp[1]-1),
                            end_point=(sp[0], sp[1]-1),
                        )
                    else:
                        yield TextNode.space(
                            start_point=(
                                last_sent.end_point[0],
                                last_sent.end_point[1]+1
                            ),
                            end_point=(
                                last_sent.end_point[0],
                                last_sent.end_point[1]+1
                            ),
                        )

                for nl in self._parse_inline(node[0]):
                    last_sent = nl
                    yield nl

            elif node[1] == self.NODE_NEWLINE_AFTER_ONE:
                self._insert_point_in_order(node[0].end_point, new_lines_after)
            elif node[1] == self.NODE_NEWLINE_AFTER_TWO:
                self._insert_point_in_order(node[0].end_point, new_lines_after, 2)

        yield from TextNode.get_new_lines(
            1,
            last_sent.end_point if last_sent else (0, 0)
        )

    def _parse_inline(self, inline_node) -> Generator[TextNode, None, None]:
        row_offset = 0
        line_offset = 0
        text = inline_node.text.decode('utf-8').strip().replace('\n', ' \n ')
        last_sent = None

        for token in text.split(' '):
            if token == '\n':
                line_offset = 0
                row_offset += 1
                continue

            if last_sent is not None and last_sent.text != '\n':
                yield TextNode(
                    text=' ',
                    start_point=(
                        inline_node.start_point[0]+row_offset,
                        inline_node.start_point[1]+line_offset
                    ),
                    end_point=(
                        inline_node.start_point[0]+row_offset,
                        inline_node.start_point[1]+line_offset+1
                    ),
                )
                line_offset += 1

            token_len = len(token)
            node = TextNode(
                text=token,
                start_point=(
                    inline_node.start_point[0]+row_offset,
                    inline_node.start_point[1]+line_offset
                ),
                end_point=(
                    inline_node.start_point[0]+row_offset,
                    inline_node.start_point[1]+line_offset+token_len
                ),
            )
            yield node

            last_sent = node
            line_offset += token_len

    @staticmethod
    def _insert_point_in_order(point, lst, times=1):
        i = 0
        length = len(lst)
        while i < length and lst[i] < point:
            i += 1

        for _ in range(times):
            lst.insert(i, point)

    def _needs_space_before(self, node, lines, last_sent) -> bool:
        if last_sent is None or last_sent.text[-1] == '\n':
            return False
        if node.start_point[0] == last_sent.end_point[0]:
            return ' ' in lines[node.start_point[0]][last_sent.end_point[1]:node.start_point[1]]
        return last_sent.text != '\n'
