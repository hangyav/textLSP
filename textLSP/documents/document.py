import logging
import tempfile
import portion as P

from typing import Optional, Generator
from dataclasses import dataclass

from lsprotocol.types import Range, Position, TextDocumentContentChangeEvent
from pygls.workspace import Document
from tree_sitter import Language, Parser, Tree, Node

from ..utils import get_class, synchronized, git_clone, get_user_cache
from .. import documents

logger = logging.getLogger(__name__)


class BaseDocument(Document):
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

    def range_at_offset(self, offset: int, length: int, cleaned=False) -> Range:
        start = self.position_at_offset(offset)
        if start is None:
            return None

        length = start.character + length
        lines = self.cleaned_lines if cleaned else self.lines
        for lidx, line in enumerate(lines[start.line:], start.line):
            line_len = len(line)
            if line_len > length:
                return Range(
                    start=start,
                    end=Position(
                        line=lidx,
                        character=length
                    )
                )
            length -= line_len


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
        super().apply_change(change)
        self._cleaned_source = None


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
            end_point=node.end_point,
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

    def __len__(self):
        return len(self.text)


class TreeSitterDocument(CleanableDocument):
    LIB_PATH_TEMPLATE = '{}/treesitter/{}.so'.format(get_user_cache(), '{}')

    def __init__(self, language_name, grammar_url, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parser = TreeSitterDocument.get_parser(language_name, grammar_url)
        self._text_intervals = None

    @staticmethod
    def build_library(name, url) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            git_clone(url, tmpdir)
            Language.build_library(
                TreeSitterDocument.LIB_PATH_TEMPLATE.format(name),
                [tmpdir]
            )

    @staticmethod
    def get_parser(name, url) -> Parser:
        parser = Parser()
        try:
            parser.set_language(
                Language(
                    TreeSitterDocument.LIB_PATH_TEMPLATE.format(name),
                    name,
                )
            )
        except Exception:
            TreeSitterDocument.build_library(name, url)
            parser.set_language(
                Language(
                    TreeSitterDocument.LIB_PATH_TEMPLATE.format(name),
                    name,
                )
            )
        return parser

    def _clean_source(self):
        tree = self._parser.parse(bytes(self.source, 'utf-8'))
        self._text_intervals = P.IntervalDict()

        offset = 0
        for node in self._iterate_text_nodes(tree):
            node_len = len(node)
            self._text_intervals[P.closed(offset, offset+node_len)] = (
                node.start_point,
                node.end_point,
                offset,
                node.text
            )
            offset += node_len

        self._cleaned_source = ''.join(v[3] for _, v in self._text_intervals.items())

    def _iterate_text_nodes(self, tree: Tree) -> Generator[TextNode, None, None]:
        raise NotImplementedError()

    def position_at_offset(self, offset: int, cleaned=False) -> Position:
        if not cleaned:
            return super().position_at_offset(offset, cleaned)

        item = self._text_intervals[offset]
        assert offset >= item[2]
        diff = offset - item[2]

        return Position(
            line=item[0][0],
            character=item[0][1]+diff,
        )

    def range_at_offset(self, offset: int, length: int, cleaned=False) -> Range:
        if not cleaned:
            return super().range_at_offset(offset, length, cleaned)

        start = self.position_at_offset(offset, cleaned)
        offset += length
        item = self._text_intervals[offset]
        item_end = item[2] + item[1][1]-item[0][1]
        assert offset <= item_end, f'{offset}, {item_end}, {item}'
        diff = item_end - offset

        end = Position(
            line=item[1][0],
            character=item[1][1]-diff,
        )

        return Range(
            start=start,
            end=end,
        )


class DocumentTypeFactory():
    TYPE_MAP = {
        'text': 'txt',
        'tex': 'latex',
    }

    @staticmethod
    def get_file_type(language_id):
        return DocumentTypeFactory.TYPE_MAP.get(language_id) or language_id

    @staticmethod
    def get_document(
        doc_uri: str,
        source: Optional[str] = None,
        version: Optional[int] = None,
        language_id: Optional[str] = None,
        sync_kind=None,
    ) -> Document:
        try:
            cls = get_class(
                '{}.{}'.format(
                    documents.__name__,
                    DocumentTypeFactory.get_file_type(language_id)
                ),
                BaseDocument,
            )
            return cls(
                uri=doc_uri,
                source=source,
                version=version,
                language_id=language_id,
                sync_kind=sync_kind
            )
        except ImportError as e:
            return BaseDocument(
                uri=doc_uri,
                source=source,
                version=version,
                language_id=language_id,
                sync_kind=sync_kind
            )
