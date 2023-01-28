from typing import Generator
from tree_sitter import Tree, Node

from ..document import TreeSitterDocument, TextNode


class OrgDocument(TreeSitterDocument):
    CONFIGURATION_TODO_KEYWORDS = 'org_todo_keywords'

    DEFAULT_TODO_KEYWORDS = {'TODO', 'DONE'}

    EXPR = 'expr'
    HEADLINE = 'headline'
    PARAGRAPH = 'paragraph'
    SECTION = 'section'
    PARAGRAPH = 'paragraph'
    ITEM = 'item'

    NODE_CONTENT = 'content'
    NODE_NEWLINE_AFTER_ONE = 'newline_after_one'
    NODE_NEWLINE_AFTER_TWO = 'newline_after_two'

    TEXT_ROOTS = {
        PARAGRAPH,
    }

    TEXT_ROOTS_WITH_ITEM = {
        HEADLINE,
    }

    NEWLINE_AFTER_ONE = {
        PARAGRAPH,
        HEADLINE,
        SECTION,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(
            'org',
            'https://github.com/milisims/tree-sitter-org',
            *args,
            **kwargs,
        )
        self._query = self._build_query()
        keywords = self.config.setdefault(
            self.CONFIGURATION_TODO_KEYWORDS,
            self.DEFAULT_TODO_KEYWORDS,
        )
        if type(keywords) != set:
            self.config[self.CONFIGURATION_TODO_KEYWORDS] = set(keywords)

    def _build_query(self):
        query_str = ''

        for root in self.TEXT_ROOTS:
            query_str += f'({root} ({self.EXPR}) @{self.NODE_CONTENT})\n'

        for root in self.TEXT_ROOTS_WITH_ITEM:
            query_str += f'({root} (item ({self.EXPR}) @{self.NODE_CONTENT}))\n'

        for root in self.NEWLINE_AFTER_ONE:
            query_str += f'({root}) @{self.NODE_NEWLINE_AFTER_ONE}\n'

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
                # check if we need newlines due to linebreaks in source
                if (
                    last_sent is not None
                    and node[0].start_point[0] - last_sent.end_point[0] > 1
                    and '' in lines[last_sent.end_point[0]+1:node[0].start_point[0]]
                ):
                    for nl_node in TextNode.get_new_lines(1, last_sent.end_point):
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

                if self._valid_content_node(node[0]):
                    last_sent = TextNode.from_ts_node(node[0])
                    yield last_sent
            elif node[1] == self.NODE_NEWLINE_AFTER_ONE:
                self._insert_point_in_order(node[0].end_point, new_lines_after)

        yield from TextNode.get_new_lines(
            1,
            last_sent.end_point if last_sent else (0, 0)
        )

    def _valid_content_node(self, node: Node):
        return not (
            node.parent is not None
            and node.parent.parent is not None
            and node.parent.parent.type == self.HEADLINE
            and node.text.decode('utf-8') in self.config[self.CONFIGURATION_TODO_KEYWORDS]
            and self.lines[node.start_point[0]][:node.start_point[1]] == '*' * max(1, node.start_point[1]-1) + ' '
        )

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
