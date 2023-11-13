import logging
import tempfile
import sys
import copy

from typing import Optional, Generator, List, Dict
from dataclasses import dataclass
from itertools import chain

from lsprotocol.types import (
    Range,
    Position,
    TextDocumentContentChangeEvent,
    TextDocumentContentChangeEvent_Type1,
    TextDocumentContentChangeEvent_Type2,
)
from pygls.workspace import Document, position_from_utf16, range_from_utf16
from tree_sitter import Language, Parser, Tree, Node

from ..utils import get_class, synchronized, git_clone, get_user_cache
from ..types import (
    OffsetPositionInterval,
    OffsetPositionIntervalList,
    Interval
)
from .. import documents

logger = logging.getLogger(__name__)


class BaseDocument(Document):
    def __init__(self, *args, config: Dict = None, **kwargs):
        super().__init__(*args, **kwargs)
        if config is None:
            self.config = dict()
        else:
            self.config = config

    @property
    def cleaned_source(self) -> str:
        return self.source

    @property
    def cleaned_lines(self):
        return self.cleaned_source.splitlines(True)

    @property
    def language(self) -> str:
        return 'en'

    def position_at_offset(self, offset: int, cleaned=False) -> Position:
        pos = 0
        lines = self.cleaned_lines if cleaned else self.lines
        for lidx, line in enumerate(lines):
            line_len = len(line)
            if pos + line_len > offset:
                return Position(
                    line=lidx,
                    character=offset-pos
                )
            pos += line_len

        assert offset == pos, 'Offset it over the document\'s end!'
        return Position(
            line=lidx,
            character=offset-pos
        )

    def range_at_offset(self, offset: int, length: int, cleaned=False) -> Range:
        start = self.position_at_offset(offset, cleaned)
        if start is None:
            return None

        if length == 0:
            return Range(
                start=start,
                end=start,
            )

        length = start.character + length
        lines = self.cleaned_lines if cleaned else self.lines
        for lidx, line in enumerate(lines[start.line:], start.line):
            line_len = len(line)
            if line_len >= length:
                return Range(
                    start=start,
                    end=Position(
                        line=lidx,
                        character=length-1
                    )
                )
            length -= line_len

        return Range(
            start=start,
            end=Position(
                line=len(lines)-1,
                character=len(lines[-1])-1
            )
        )

    def offset_at_position(self, position: Position, cleaned=False) -> int:
        # doesn't really matter
        lines = self.cleaned_lines if cleaned else self.lines
        pos = position_from_utf16(lines, position)
        row, col = pos.line, pos.character
        return col + sum(len(line) for line in lines[:row])

    def text_at_offset(self, offset: int, length: int, cleaned=False) -> Interval:
        source = self.cleaned_source if cleaned else self.source
        return source[offset:offset+length]

    def sentence_at_offset(self, offset: int, min_length=0, cleaned=False) -> Interval:
        start_idx = offset
        end_idx = offset
        source = self.cleaned_source if cleaned else self.source
        len_source = len(source)

        assert start_idx >= 0
        assert end_idx < len_source

        while True:
            if start_idx - 2 < 0:
                start_idx = 0
                break
            if source[start_idx-2] in {'.', '!', '?'} and source[start_idx-1] in {' ', '\n'}:
                break
            start_idx -= 1

        while end_idx < len_source-1:
            if (
                    end_idx >= 1
                    and source[end_idx-1] in {'.', '!', '?'}
                    and source[end_idx in {' ', '\n'}]
                    and end_idx-start_idx+1 >= min_length
            ):
                break
            end_idx += 1

        return Interval(start_idx, end_idx-start_idx+1)

    def paragraph_at_offset(self, offset: int, min_length=0, min_offset=0, cleaned=False) -> Interval:
        """
        returns (start_offset, length)
        """
        start_idx = offset
        end_idx = offset
        source = self.cleaned_source if cleaned else self.source
        len_source = len(source)

        assert start_idx >= 0
        assert end_idx < len_source

        while (
            start_idx >= 0
            and not (
                all(source[start_idx-i] == '\n' for i in range(1, min(3, start_idx+1)))
                or all(source[start_idx-i] == '\n' for i in range(min(2, start_idx+1)))  # empty line
            )
        ):
            start_idx -= 1

        while True:
            while (
                end_idx < len_source-1
                and not (
                    all(source[end_idx+i] == '\n' for i in range(min(2, len_source-end_idx)))
                    or all(source[start_idx-i] == '\n' for i in range(min(2, start_idx+1)))  # empty line
                )
            ):
                end_idx += 1

            if end_idx < len_source-1 and (end_idx-start_idx+1 < min_length or end_idx <= min_offset):
                end_idx += 1
            else:
                break

        return Interval(start_idx, end_idx-start_idx+1)

    def paragraph_at_position(self, position: Position, cleaned=False) -> Interval:
        offset = self.offset_at_position(position, cleaned)
        if offset is None:
            return None
        return self.paragraph_at_offset(offset, cleaned=cleaned)

    def paragraphs_at_offset(self, offset: int, min_length=0, min_offset=0, cleaned=False) -> List[Interval]:
        res = list()
        doc_length = len(self.cleaned_source if cleaned else self.source)
        length = 0

        while offset < doc_length and (length < min_length or offset <= min_offset or length == 0):
            paragraph = self.paragraph_at_offset(offset, cleaned=cleaned)
            res.append(paragraph)

            offset = paragraph.start + paragraph.length
            length += paragraph.length

        return res

    def paragraphs_at_range(self, position_range: Range, cleaned=False) -> List[Interval]:
        res = list()
        source = self.cleaned_source if cleaned else self.source
        position = position_range.start

        while position < position_range.end:
            paragraph = self.paragraph_at_position(position, cleaned)
            if paragraph is None:
                continue
            res.append(paragraph)
            text = source[paragraph.start:paragraph.start+paragraph.length].splitlines()
            line = position.line+len(text)
            char = 0
            position = Position(
                line=line,
                character=char
            )

        return res

    def last_position(self, cleaned=False):
        lines = self.cleaned_lines if cleaned else self.lines
        return Position(
            line=(len(lines)-1),
            character=len(lines[-1])-1
        )


class CleanableDocument(BaseDocument):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cleaned_source = None

    @property
    def cleaned_source(self) -> str:
        if self._cleaned_source is None:
            self._sync_clean_source()
        return self._cleaned_source

    @synchronized
    def _sync_clean_source(self):
        # just so that implementations don't need to remember to use
        # synchronized
        self._clean_source()

    def _clean_source(self):
        raise NotImplementedError()

    def apply_change(self, change: TextDocumentContentChangeEvent) -> None:
        self._cleaned_source = None
        super().apply_change(change)

    def position_at_offset(self, offset: int, cleaned=False) -> Position:
        if not cleaned:
            return super().position_at_offset(offset, cleaned)

        raise NotImplementedError()

    def range_at_offset(self, offset: int, length: int, cleaned=False) -> Range:
        if not cleaned:
            return super().range_at_offset(offset, length, cleaned)

        raise NotImplementedError()

    def offset_at_position(self, position: Position, cleaned=False) -> int:
        if not cleaned:
            return super().offset_at_position(position, cleaned)

        raise NotImplementedError()

    def paragraphs_at_range(self, position_range: Range, cleaned=False) -> Interval:
        if not cleaned:
            return super().paragraphs_at_range(position_range, cleaned)

        raise NotImplementedError()

    def last_position(self, cleaned=False):
        if not cleaned:
            return super().last_position(cleaned)

        raise NotImplementedError()


@dataclass
class TextNode():
    text: str
    start_point: tuple
    end_point: tuple

    @staticmethod
    def from_ts_node(node: Node):
        return TextNode(
            text=node.text.decode('utf-8'),
            start_point=node.start_point,
            end_point=(node.end_point[0], node.end_point[1]-1)
        )

    @staticmethod
    def space(start_point: tuple, end_point: tuple):
        return TextNode(
            text=' ',
            start_point=start_point,
            end_point=end_point,
        )

    @staticmethod
    def new_line(start_point: tuple, end_point: tuple):
        return TextNode(
            text='\n',
            start_point=start_point,
            end_point=end_point,
        )

    @staticmethod
    def get_new_lines(num, location):
        for i in range(num):
            yield TextNode.new_line(
                start_point=(
                    location[0],
                    location[1]+i+1,
                ),
                end_point=(
                    location[0],
                    location[1]+i+1,
                ),
            )

    def __len__(self):
        return len(self.text)


class TreeSitterDocument(CleanableDocument):
    LIB_PATH_TEMPLATE = '{}/treesitter/{}.so'.format(get_user_cache(), '{}')

    def __init__(self, language_name, grammar_url, branch, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #######################################################################
        # Do not deepcopy these
        self._language = self.get_language(language_name, grammar_url, branch)
        self._parser = self.get_parser(
            language_name,
            grammar_url,
            branch,
            self._language
        )
        self._tree = None
        self._query = self._build_query()
        #######################################################################

        self._text_intervals = None

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k not in {'_language', '_parser', '_tree', '_query'}:
                setattr(result, k, copy.deepcopy(v, memo))
            else:
                setattr(result, k, v)
        return result

    @classmethod
    def build_library(cls, name, url, branch=None) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            git_clone(url, tmpdir, branch)
            Language.build_library(
                cls.LIB_PATH_TEMPLATE.format(name),
                [tmpdir]
            )

    @classmethod
    def get_language(cls, name, url, branch=None) -> Language:
        try:
            return Language(
                cls.LIB_PATH_TEMPLATE.format(name),
                name,
            )
        except Exception:
            cls.build_library(name, url, branch)
            return Language(
                cls.LIB_PATH_TEMPLATE.format(name),
                name,
            )

    @classmethod
    def get_parser(cls, name=None, url=None, branch=None, language=None) -> Parser:
        parser = Parser()
        if language is None:
            assert name is not None
            assert url is not None
            language = cls.get_language(name, url, branch)
        parser.set_language(language)
        return parser

    def _build_query(self):
        raise NotImplementedError()

    def _parse_source(self):
        return self._parser.parse(bytes(self.source, 'utf-8'))

    @property
    def tree(self) -> Tree:
        if self._tree is None:
            self._tree = self._parse_source()
        return self._tree

    def _clean_source(self, change: TextDocumentContentChangeEvent_Type1 = None):
        self._text_intervals = OffsetPositionIntervalList()

        offset = 0
        start_point = (0, 0)
        end_point = (sys.maxsize, sys.maxsize)
        for node in self._iterate_text_nodes(self.tree, start_point, end_point):
            node_len = len(node)
            self._text_intervals.add_interval_values(
                    offset,
                    offset+node_len-1,
                    node.start_point[0],
                    node.start_point[1],
                    node.end_point[0],
                    node.end_point[1],
                    node.text,
            )
            offset += node_len

        self._cleaned_source = ''.join(self._text_intervals.values)

    def _iterate_text_nodes(
            self,
            tree: Tree,
            start_point,
            end_point,
    ) -> Generator[TextNode, None, None]:
        raise NotImplementedError()

    def _get_edit_positions(self, change):
        lines = self.lines
        change_range = change.range
        change_range = range_from_utf16(lines, change_range)
        start_line = change_range.start.line
        start_col = change_range.start.character
        end_line = change_range.end.line
        end_col = change_range.end.character
        len_lines = len(lines)
        if len_lines == 0:
            start_byte = 0
            end_byte = 0
        else:
            if end_line >= len(lines):
                # this could happen eg when the last line is deleted
                end_line = len(lines) - 1
                end_col = len(lines[end_line]) - 1

            start_byte = len(bytes(
                ''.join(
                    lines[:start_line] + [lines[start_line][:start_col]]
                ),
                'utf-8',
            ))
            end_byte = len(bytes(
                ''.join(
                    lines[:end_line] + [lines[end_line][:end_col]]
                ),
                'utf-8',
            ))
        text_bytes = len(bytes(change.text, 'utf-8'))

        if end_byte - start_byte == 0:
            # INSERT
            old_end_byte = start_byte
            new_end_byte = start_byte + text_bytes
            start_point = (start_line, start_col)
            old_end_point = start_point
            new_lines = change.text.count('\n')
            new_end_point = (
                start_line + new_lines,
                (start_col + text_bytes) if new_lines == 0 else len(bytes(
                    change.text.split('\n')[-1],
                    'utf-8'
                )),
            )
        elif text_bytes == 0:
            # DELETE
            old_end_byte = end_byte
            new_end_byte = start_byte
            start_point = (start_line, start_col)
            old_end_point = (end_line, end_col)
            new_end_point = start_point
        else:
            # REPLACE
            old_end_byte = end_byte
            new_end_byte = start_byte + text_bytes
            start_point = (start_line, start_col)
            old_end_point = (end_line, end_col)

            new_lines = change.text.count('\n')
            deleted_lines = end_line - start_line
            if new_lines == 0 and deleted_lines == 0:
                new_end_line = end_line
                new_end_col = end_col + text_bytes - (end_col - start_col)
            elif new_lines > 0 and deleted_lines == 0:
                new_end_line = end_line + new_lines
                new_end_col = len(bytes(change.text.split('\n')[-1], 'utf-8'))
            elif new_lines == 0 and deleted_lines > 0:
                new_end_line = end_line - deleted_lines
                new_end_col = end_col + text_bytes - (end_col - start_col)
            else:
                new_end_line = end_line + new_lines - deleted_lines
                new_end_col = len(bytes(change.text.split('\n')[-1], 'utf-8'))

            new_end_point = (
                new_end_line,
                new_end_col,
            )

        return (
                start_line,
                start_col,
                end_line,
                end_col,
                start_byte,
                old_end_byte,
                new_end_byte,
                text_bytes,
                start_point,
                old_end_point,
                new_end_point,
        )

    def _get_last_node_for_edit(self, tree, start_point, end_point):
        node = None
        capture = self._query.captures(
            tree.root_node,
        )
        if len(capture) == 0:
            return None, None

        old_tree_end_point = capture[-1][0].end_point

        if start_point == end_point:
            # avoid empty interval
            end_point = (end_point[0], end_point[1]+1)
        while True:
            nodes = self._query.captures(
                tree.root_node,
                start_point=start_point,
                end_point=end_point
            )

            if len(nodes) > 0:
                node = nodes[-1]
                break

            start_point = (start_point[0]-1, 0)
            if start_point[0] < 0:
                return None, None

        return Range(
                start=Position(*node[0].start_point),
                end=Position(*node[0].end_point)
            ), old_tree_end_point

    def _get_node_and_iterator_for_edit(
            self,
            start_point,
            old_end_point,
            new_end_point,
            last_changed_point,
            old_tree_end_point,
    ):
        sp = start_point
        # last_changed_point is needed to handle subtrees being broken into
        # multiple ones
        ep = max(new_end_point, last_changed_point)

        if start_point > old_tree_end_point:
            # edit at the end of the file
            # need to extend the range to include the last node since there
            # might be relevant content (e.g. multiple newlines) that was
            # ignored since it was at the end
            if old_end_point[1] > 0:
                sp = (old_tree_end_point[0], max(0, old_tree_end_point[1]-1))
            else:
                sp = (max(0, old_tree_end_point[0]-1), 0)

        node_iter = self._iterate_text_nodes(self.tree, sp, ep)
        node = next(node_iter)
        while node.text == '\n' and node.start_point == (0, 1) and node.end_point == (0, 1):
            # empty tree is selected
            assert next(node_iter, None) is None
            if sp > (0, 0):
                sp = (max(0, sp[0]-1), 0)
            else:
                node.start_point = start_point
                node.end_point = start_point
                break

            node_iter = self._iterate_text_nodes(self.tree, sp, ep)
            node = next(node_iter)

        return node, chain([node], node_iter)

    def _get_intervals_before_edit(
            self,
            node,
    ):
        # offset = 0
        for interval_idx in range(len(self._text_intervals)):
            interval = self._text_intervals.get_interval(interval_idx)
            if interval.value == '\n' and interval.position_range.start == interval.position_range.end:
                # newline added by parser but not in source
                interval_end = (interval.position_range.end.line+1, 0)
                if interval_end >= node.start_point:
                    # FIXME This is very messy. Handling these dummy newlines
                    # should be refactored.
                    interval.value = ' '
                    # offset += len(interval.value)
                    # text_intervals.add_interval(interval)
                    yield interval
                    break
            else:
                interval_end = (
                    interval.position_range.end.line,
                    interval.position_range.end.character,
                )
                if interval_end >= node.start_point:
                    break

            # offset += len(interval.value)
            # text_intervals.add_interval(interval)
            yield interval

    def _get_edited_intervals_and_last_node(
            self,
            node_iter,
            offset,
    ):
        tmp_intvals = list()
        last_new_node = None
        tmp_node = None
        for node in node_iter:
            node_len = len(node)
            tmp_intvals.append(
                OffsetPositionInterval(
                    offset_interval=Interval(
                        start=offset,
                        length=node_len
                    ),
                    position_range=Range(
                        start=Position(
                            line=node.start_point[0],
                            character=node.start_point[1],
                        ),
                        end=Position(
                            line=node.end_point[0],
                            character=node.end_point[1],
                        ),
                    ),
                    value=node.text,
                )
            )
            offset += node_len
            last_new_node = tmp_node
            tmp_node = node

        return tmp_intvals, last_new_node

    def _get_idx_after_edited_tree(
        self,
        old_end_point,
        new_end_point,
        last_new_end_point,
        last_changed_point
    ):
        row_diff = new_end_point[0] - old_end_point[0]
        if last_new_end_point[0] < new_end_point[0]:
            # parse ended before the edit, happens when non parseable
            # part is edited or all content was deleted
            last_new_end_point = (
                max(old_end_point, new_end_point)[0],
                max(old_end_point, new_end_point)[1] + 1
            )
        elif last_new_end_point[0] > new_end_point[0]:
            # parse ended in a later line  as the edit, i.e. its
            # position is only affected by line shift
            last_new_end_point = (
                # last_new_end_point[0] - row_diff,
                # last_new_end_point[1] + 1
                max(last_changed_point, last_new_end_point)[0] - row_diff,
                max(last_changed_point, last_new_end_point)[1] + 1
            )
        elif row_diff == 0:
            # the parse ended in the line of the edit
            last_new_end_point = (
                last_new_end_point[0],
                last_new_end_point[1] - (new_end_point[1] - old_end_point[1])+1
            )
        elif row_diff > 0:
            # the edit was in the line of the last node which is now
            # shifted
            last_new_end_point = (
                last_new_end_point[0] - row_diff,
                old_end_point[1] + last_new_end_point[1] - new_end_point[1] + 1
            )
        else:
            # the edit was in the line of the last node which is now
            # shifted
            last_new_end_point = (
                last_new_end_point[0] - row_diff,
                new_end_point[1] + last_new_end_point[1] - old_end_point[1] + 1
            )

        last_idx = self._text_intervals.get_idx_at_position(
            Position(
                line=max(0, last_new_end_point[0]),
                character=max(0, last_new_end_point[1])
            ),
            strict=False,
        )
        return last_idx

    def _handle_intervals_after_edit_shifted(
            self,
            last_idx,
            start_col,
            end_line,
            end_col,
            old_end_point,
            new_end_point,
            text_bytes,
            offset,
            text_intervals,
    ):
        while last_idx > 0:
            interval = self._text_intervals.get_interval(last_idx-1)
            if (interval.value != '\n' or interval.position_range.start !=
                    interval.position_range.end):
                # not dummy newline
                break
            last_idx -= 1

        row_diff = new_end_point[0] - old_end_point[0]
        col_diff = text_bytes - (end_col - start_col)
        for interval_idx in range(last_idx, len(self._text_intervals)):
            interval = self._text_intervals.get_interval(interval_idx)
            if (
                len(text_intervals) == 0
                and interval.value.count('\n') > 0
                and interval.value.strip() == ''
            ):
                continue
            node_len = len(interval.value)
            if interval.position_range.start.line > end_line:
                start_line_offset = row_diff
                start_char_offset = 0
                end_line_offset = row_diff
                end_char_offset = 0
            elif (interval.position_range.start.line == end_line
                  and interval.position_range.start.character >= end_col):
                start_line_offset = row_diff
                start_char_offset = col_diff
                end_line_offset = row_diff
                if interval.position_range.end.line > interval.position_range.start.line:
                    end_char_offset = 0
                else:
                    end_char_offset = col_diff
            else:
                # These are the special newlines which are not in the source
                # but added by the parser to separate paragraphs
                assert (interval.value == '\n' and interval.position_range.start ==
                        interval.position_range.end)
                last_interval_range = text_intervals.get_interval(-1).position_range
                interval_range = interval.position_range
                # we need to set start and end position to the same value
                # which is the same line as the last item in text_intervals
                # and one column to the right
                end_line_offset = last_interval_range.end.line - interval_range.end.line
                start_line_offset = interval_range.end.line - interval_range.start.line + end_line_offset
                end_char_offset = last_interval_range.end.character - interval_range.end.character + 1
                start_char_offset = interval_range.end.character - interval_range.start.character + end_char_offset

            text_intervals.add_interval_values(
                offset,
                offset+node_len-1,
                interval.position_range.start.line + start_line_offset,
                interval.position_range.start.character + start_char_offset,
                interval.position_range.end.line + end_line_offset,
                interval.position_range.end.character + end_char_offset,
                interval.value,
            )
            offset += node_len

    def _build_updated_text_intervals(
            self,
            start_line,
            start_col,
            end_line,
            end_col,
            start_byte,
            old_end_byte,
            new_end_byte,
            start_point,
            old_end_point,
            new_end_point,
            text_bytes,
            last_changed_point,
            old_tree_end_point,
    ):
        text_intervals = OffsetPositionIntervalList()

        # get first edited node and iterator for all edited nodes
        node, node_iter = self._get_node_and_iterator_for_edit(
            start_point,
            old_end_point,
            new_end_point,
            last_changed_point,
            old_tree_end_point,
        )

        # copy the text intervals up to the start of the change
        for interval in self._get_intervals_before_edit(node):
            text_intervals.add_interval(interval)

        if len(text_intervals) > 0:
            offset = interval.offset_interval.start + interval.offset_interval.length
        else:
            offset = 0

        # handle the nodes that were in the edited subtree
        new_intervals, last_new_node = self._get_edited_intervals_and_last_node(
            node_iter,
            offset,
        )
        if last_new_node is None:
            return None

        for interval in new_intervals[:-1]:
            # there's always a newline return at the end of the file which
            # is not needed if we are not really at the end of the file yet
            # text_intervals.add_interval_values(*interval)
            text_intervals.add_interval(interval)
        offset = interval.offset_interval.start + interval.offset_interval.length

        # add remaining intervals shifted
        last_new_end_point = last_new_node.end_point
        last_idx = self._get_idx_after_edited_tree(
            old_end_point,
            new_end_point,
            last_new_end_point,
            last_changed_point
        )
        if last_idx+1 >= len(self._text_intervals):
            # we are actully at the end of the file so add the final newline
            text_intervals.add_interval(new_intervals[-1])
        else:
            self._handle_intervals_after_edit_shifted(
                    last_idx,
                    start_col,
                    end_line,
                    end_col,
                    old_end_point,
                    new_end_point,
                    text_bytes,
                    offset,
                    text_intervals,
            )

        return text_intervals

    def _apply_incremental_change(self, change: TextDocumentContentChangeEvent_Type1) -> None:
        """Apply an ``Incremental`` text change to the document"""
        if self._tree is None:
            super()._apply_incremental_change(change)
            return

        tree = self.tree
        (
                start_line,
                start_col,
                end_line,
                end_col,
                start_byte,
                old_end_byte,
                new_end_byte,
                text_bytes,
                start_point,
                old_end_point,
                new_end_point,
        ) = self._get_edit_positions(change)

        # bookkeeping for later source cleaning
        # TODO remove this part
        (
            old_last_edited_node,
            old_tree_end_point
        ) = self._get_last_node_for_edit(
            tree,
            start_point,
            old_end_point,
        )

        tree.edit(
            start_byte=start_byte,
            old_end_byte=old_end_byte,
            new_end_byte=new_end_byte,
            start_point=start_point,
            old_end_point=old_end_point,
            new_end_point=new_end_point,
        )
        super()._apply_incremental_change(change)
        new_source = bytes(self.source, 'utf-8')
        self._tree = self._parser.parse(
            new_source,
            tree
        )

        last_changed_point = (0, 0)
        for change in tree.get_changed_ranges(self.tree):
            last_changed_point = max(last_changed_point, change.end_point)

        if old_tree_end_point is not None:
            # rebuild the cleaned source
            text_intervals = self._build_updated_text_intervals(
                start_line,
                start_col,
                end_line,
                end_col,
                start_byte,
                old_end_byte,
                new_end_byte,
                start_point,
                old_end_point,
                new_end_point,
                text_bytes,
                last_changed_point,
                old_tree_end_point,
            )

            if text_intervals is not None:
                self._text_intervals = text_intervals
                self._cleaned_source = ''.join(self._text_intervals.values)
        else:
            self._clean_source()

    def _apply_full_change(self, change: TextDocumentContentChangeEvent) -> None:
        """Apply a ``Full`` text change to the document."""
        super()._apply_full_change(change)
        self._tree = None

    def position_at_offset(self, offset: int, cleaned=False) -> Position:
        if not cleaned:
            return super().position_at_offset(offset, cleaned)

        if self._cleaned_source is None:
            self._clean_source()

        item = self._text_intervals.get_interval_at_offset(offset)
        assert offset >= item.offset_interval.start
        diff = offset - item.offset_interval.start

        return Position(
            line=item.position_range.start.line,
            character=item.position_range.start.character+diff,
        )

    def range_at_offset(self, offset: int, length: int, cleaned=False) -> Range:
        if not cleaned:
            return super().range_at_offset(offset, length, cleaned)

        start = self.position_at_offset(offset, cleaned)
        if length == 0:
            return Range(
                start=start,
                end=start,
            )

        offset += length
        item = self._text_intervals.get_interval_at_offset(offset-1)
        item_end = item.offset_interval.start + item.offset_interval.length
        assert offset <= item_end, f'{offset}, {item_end}, {item}'
        diff = item_end - offset

        end = Position(
            line=item.position_range.end.line,
            character=item.position_range.end.character-diff,
        )

        return Range(
            start=start,
            end=end,
        )

    def offset_at_position(self, position: Position, cleaned=False) -> int:
        if not cleaned:
            return super().offset_at_position(position, cleaned)

        if self._cleaned_source is None:
            self._clean_source()

        item = self._text_intervals.get_interval_at_position(position, False)

        if (
            item.position_range.end.line == position.line
            and item.position_range.start.character <= position.character
        ):
            diff = position.character - item.position_range.start.character
            return item.offset_interval.start + diff
        return item.offset_interval.start

    def paragraphs_at_range(self, position_range: Range, cleaned=False) -> List[Interval]:
        if not cleaned:
            return super().paragraphs_at_range(position_range, cleaned)

        if self._cleaned_source is None:
            self._clean_source()

        res = list()
        res_set = set()

        idx = self._text_intervals.get_idx_at_position(
            position_range.start,
            strict=False
        )
        for i in range(idx, len(self._text_intervals)):
            interval = self._text_intervals.get_interval(i)
            if interval.position_range.start > position_range.end:
                break

            paragraph = self.paragraph_at_offset(
                interval.offset_interval.start,
                min_length=interval.offset_interval.length,
                cleaned=True
            )
            if paragraph is not None and paragraph not in res_set:
                res.append(paragraph)
                res_set.add(paragraph)

        return res

    def last_position(self, cleaned=False):
        if not cleaned:
            return super().last_position(cleaned)

        if self._cleaned_source is None:
            self._clean_source()

        last = self._text_intervals.get_interval(len(self._text_intervals)-1)
        return last.position_range.end


class DocumentTypeFactory():
    TYPE_MAP = {
        'text': 'txt',
        'tex': 'latex',
        'md': 'markdown',
    }

    @staticmethod
    def get_file_type(language_id):
        return DocumentTypeFactory.TYPE_MAP.get(language_id) or language_id

    @staticmethod
    def get_document(
        doc_uri: str,
        config: Dict,
        source: Optional[str] = None,
        version: Optional[int] = None,
        language_id: Optional[str] = None,
        sync_kind=None,
    ) -> Document:
        try:
            type = DocumentTypeFactory.get_file_type(language_id)
            cls = get_class(
                '{}.{}'.format(
                    documents.__name__,
                    type,
                ),
                BaseDocument,
            )
            return cls(
                config=config.get(type, dict()),
                uri=doc_uri,
                source=source,
                version=version,
                language_id=language_id,
                sync_kind=sync_kind
            )
        except ImportError:
            return BaseDocument(
                config=dict(),
                uri=doc_uri,
                source=source,
                version=version,
                language_id=language_id,
                sync_kind=sync_kind
            )


class ChangeTracker():
    def __init__(self, doc: BaseDocument, cleaned=False):
        self.document = None
        self._set_document(doc)
        self.cleaned = cleaned
        length = len(doc.cleaned_source) if cleaned else len(doc.source)
        # list of tuples (span_length, was_changed)
        # negative span_length means that the span was deleted
        self._items = [(length, False)]
        self.full_document_change = False

    def _set_document(self, doc: BaseDocument):
        # XXX not too memory efficient
        self.document = copy.deepcopy(doc)

    def update_document(
            self,
            change: TextDocumentContentChangeEvent,
            updated_doc: BaseDocument
    ):
        if self.full_document_change:
            return

        if type(change) == TextDocumentContentChangeEvent_Type2:
            self.full_document_change = True
            self._items = [(-1, True)]
            return

        new_lst = list()
        start_offset = self.document.offset_at_position(
            change.range.start,
            self.cleaned,
        )
        end_offset = self.document.offset_at_position(
            change.range.end,
            self.cleaned,
        )

        item_idx, item_offset = self._get_offset_idx(start_offset)
        change_length = len(change.text)
        range_length = end_offset-start_offset
        relative_start_offset = start_offset - item_offset

        if relative_start_offset > 0:
            # add item from the beginning of the item to the start of the change
            new_lst.append((relative_start_offset, self._items[item_idx][1]))

        if start_offset == end_offset and change_length == 0:
            # nothing to do (I'm not sure what this is)
            self._set_document(updated_doc)
            return

        if change_length == 0:
            # deletion
            new_lst.append((0, True))

            tmp_item = (
                self._items[item_idx][0]-relative_start_offset-range_length,
                self._items[item_idx][1]
            )
            if tmp_item[0] != 0:
                new_lst.append(tmp_item)
        elif range_length == 0:
            # insertion
            new_lst.append((change_length, True))

            tmp_item = (
                self._items[item_idx][0]-relative_start_offset,
                self._items[item_idx][1]
            )
            if tmp_item[0] > 0:
                new_lst.append(tmp_item)
        else:
            # replacement
            new_lst.append((change_length, True))

            tmp_item = (
                self._items[item_idx][0]-relative_start_offset-(change_length-range_length),
                self._items[item_idx][1]
            )
            if tmp_item[0] > 0:
                new_lst.append(tmp_item)

        self._replace_at(item_idx, new_lst)
        self._set_document(updated_doc)

    def _get_offset_idx(self, offset):
        pos = 0
        idx = 0
        len_items = len(self._items)

        while pos <= offset and idx < len_items-1 and pos+self._items[idx][0] <= offset:
            pos += max(0, self._items[idx][0])
            idx += 1

        return idx, pos

    def _replace_at(self, idx, tuples):
        length = len(tuples)
        assert length > 0
        self._items[idx] = tuples[0]
        for i in range(1, length):
            self._items.insert(idx+i, tuples[i])

    def get_changes(self) -> List[Interval]:
        if self.cleaned:
            doc_length = len(self.document.cleaned_source)
        else:
            doc_length = len(self.document.source)

        if self.full_document_change:
            return [Interval(0, doc_length)]

        res = list()
        seen = set()
        pos = 0
        for item in self._items:
            if item[1]:
                length = item[0]
                if length < 0:
                    position = max(0, pos+length)
                    # use pos instead of position since the doc_length will change after modification
                    length = min(length*-1, doc_length-pos)
                else:
                    position = pos

                if position >= doc_length:
                    position = doc_length-1
                    length = 0

                if length == 0 and position > 0:
                    position -= 1
                    length = 1

                intv = Interval(position, length)

                if intv not in seen:
                    res.append(intv)
                    seen.add(intv)
            pos += max(0, item[0])

        return res

    def __len__(self):
        return len([item for item in self._items if item[1]])
