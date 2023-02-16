from typing import Generator
from tree_sitter import Tree

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

    NODE_CONTENT = 'content'
    NODE_NEWLINE_BEFORE_AFTER = 'newline_before_after'

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
        self._query = self._build_query()

    def _build_query(self):
        query_str = ''

        for root in self.TEXT_ROOTS:
            query_str += f'({root} ({self.TEXT} ({self.WORD}) @{self.NODE_CONTENT}))\n'

        for root in self.NEWLINE_BEFORE_AFTER_CURLY_PARENT:
            query_str += f'({root} ({self.CURLY_GROUP}) @{self.NODE_NEWLINE_BEFORE_AFTER})\n'
        for root in self.NEWLINE_BEFORE_AFTER:
            query_str += f'({root}) @{self.NODE_NEWLINE_BEFORE_AFTER}\n'

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
                        for nl in TextNode.get_new_lines(2, last_sent.end_point):
                            last_sent = nl
                            yield nl
                    new_lines_after.pop(0)
                else:
                    break

            if node[1] == self.NODE_CONTENT:
                # check if we need newlines due to linebreaks in source
                if (
                    last_sent is not None
                    and last_sent.text[-1] != '\n'
                    and node[0].start_point[0] - last_sent.end_point[0] > 1
                    and '' in lines[last_sent.end_point[0]+1:node[0].start_point[0]]
                ):
                    for nl_node in TextNode.get_new_lines(2, last_sent.end_point):
                        yield nl_node
                        last_sent = nl_node

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

                ###############################################################
                # XXX This is a workaround to handle the issues related to
                # commas and hyphens in the TS grammar. See:
                # - https://github.com/latex-lsp/tree-sitter-latex/issues/73
                # - https://github.com/latex-lsp/tree-sitter-latex/issues/74
                # and remove this block when the issues are fixed.
                line = self.lines[node[0].end_point[0]]
                char = None
                if node[0].end_point[1] < len(line):
                    char = line[node[0].end_point[1]]

                if char in {',', '-'}:
                    last_sent = TextNode(
                        text=node[0].text.decode('utf-8')+char,
                        start_point=node[0].start_point,
                        end_point=(node[0].end_point[0], node[0].end_point[1])  # node.end_point[1]-1+1
                    )
                else:
                    ###########################################################
                    last_sent = TextNode.from_ts_node(node[0])
                yield last_sent
            elif node[1] == self.NODE_NEWLINE_BEFORE_AFTER:
                new_lines_after.append(node[0].end_point)
                if last_sent is not None:
                    for nl_node in TextNode.get_new_lines(2, last_sent.end_point):
                        yield nl_node
                        last_sent = nl_node

        yield from TextNode.get_new_lines(
            1,
            last_sent.end_point if last_sent else (0, 0)
        )

    def _needs_space_before(self, node, lines, last_sent) -> bool:
        if last_sent is None or last_sent.text[-1] == '\n':
            return False
        if node.start_point[0] == last_sent.end_point[0]:
            return ' ' in lines[node.start_point[0]][last_sent.end_point[1]:node.start_point[1]]
        return last_sent.text != '\n'
