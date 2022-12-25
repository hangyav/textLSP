import logging

from typing import Optional

from lsprotocol.types import Range, Position, TextDocumentContentChangeEvent
from pygls.workspace import Document
from tree_sitter import Language, Parser

from ..utils import get_class, synchronized
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
        if self._cleaned_source is not None:
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
        self._clean_source = None


class TreeSitterDocument(CleanableDocument):
    LIB_PATH_TEMPLATE = 'build/{}.so'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def build_library(name, url) -> None:
        # TODO git checkout parser repo
        Language.build_library(
            TreeSitterDocument.LIB_PATH_TEMPLATE.format(name),
            [url]
        )

    @staticmethod
    def get_parser(name) -> Parser:
        parser = Parser()
        parser.set_language(
            Language(
                TreeSitterDocument.LIB_PATH_TEMPLATE.format(name),
                name,
            )
        )
        return parser

    def _clean_source(self):
        # TODO build the parse tree with
        # intervals lib: https://github.com/AlexandreDecan/portion
        # use the iterate nodes to get elements
        raise NotImplementedError()

    def _iterate_text_nodes(self):
        raise NotImplementedError()

    def position_at_offset(self, offset: int, cleaned=False) -> Position:
        if not cleaned:
            return super().position_at_offset(offset, False)
        raise NotImplementedError()

    def range_at_offset(self, offset: int, length: int, cleaned=False) -> Range:
        if not cleaned:
            return super().range_at_offset(offset, length, False)
        raise NotImplementedError()


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
        except ImportError:
            return BaseDocument(
                uri=doc_uri,
                source=source,
                version=version,
                language_id=language_id,
                sync_kind=sync_kind
            )
