from typing import Generator
from tree_sitter import Tree

from ..document import TreeSitterDocument, TextNode


class MarkDownDocument(TreeSitterDocument):
    SUBFOLDER_MARKDOWN = 'tree-sitter-markdown'
    SUBFOLDER_MARKDOWN_INLINE = 'tree-sitter-markdown-inline'

    TEXT = 'text'
    PARAGRAPH = 'paragraph'
    HEADING_CONTENT = 'heading_content'
    ATX_HEADING = 'atx_heading'
    LINK_TEXT = 'link_text'
    LINK_LABEL = 'link_label'
    LINK_TITLE = 'link_title'
    EMPHASIS = 'emphasis'
    STRONG_EMPHASIS = 'strong_emphasis'
    STRIKETHROUGH = 'strikethrough'
    IMAGE_DESCRIPTION = 'image_description'
    TABLE_CELL = 'table_cell'

    NODE_CONTENT = 'content'
    NODE_NEWLINE_AFTER_ONE = 'newline_after_one'
    NODE_NEWLINE_AFTER_TWO = 'newline_after_two'

    ROOTS_WITH_TEXT = {
        PARAGRAPH,
        HEADING_CONTENT,
        LINK_TEXT,
        LINK_LABEL,
        LINK_TITLE,
        EMPHASIS,
        STRONG_EMPHASIS,
        STRIKETHROUGH,
        IMAGE_DESCRIPTION,
        TABLE_CELL,
    }

    NEWLINE_AFTER_ONE = {
    }

    NEWLINE_AFTER_TWO = {
        PARAGRAPH,
        ATX_HEADING,
        TABLE_CELL,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(
            'markdown',
            'https://github.com/ikatyang/tree-sitter-markdown',
            *args,
            **kwargs,
        )
        self._query = self._build_query()

    def _build_query(self):
        query_str = ''

        for root in self.ROOTS_WITH_TEXT:
            query_str += f'({root} ({self.TEXT}) @{self.NODE_CONTENT})\n'

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
                if len(node[0].text.decode('utf-8').strip()) == 0:
                    continue
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

                for nl in self._handle_text_nodes(node[0]):
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

    def _handle_text_nodes(self, inline_node) -> Generator[TextNode, None, None]:
        line_offset = 0
        text = inline_node.text.decode('utf-8').strip()
        last_sent = None

        for token in text.split():
            if last_sent is not None:
                yield TextNode(
                    text=' ',
                    start_point=(
                        inline_node.start_point[0],
                        inline_node.start_point[1]+line_offset
                    ),
                    end_point=(
                        inline_node.start_point[0],
                        inline_node.start_point[1]+line_offset+1
                    ),
                )
                line_offset += 1

            token_len = len(token)
            node = TextNode(
                text=token,
                start_point=(
                    inline_node.start_point[0],
                    inline_node.start_point[1]+line_offset
                ),
                end_point=(
                    inline_node.start_point[0],
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
            text = node.text.decode('utf-8')
            # text nodes contain whitespaces which can lead to errors
            # E.g.: |~~This~~| is a text|
            diff = len(text) - len(text.lstrip())
            return ' ' in lines[node.start_point[0]][last_sent.end_point[1]:node.start_point[1]+diff]
        return last_sent.text != '\n'
