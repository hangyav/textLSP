import logging

from typing import Optional

from lsprotocol.types import Range, Position
from pygls.workspace import Workspace, Document

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


class DocumentTypeFactory():
    @staticmethod
    def get_document(
        doc_uri: str,
        source: Optional[str] = None,
        version: Optional[int] = None,
        language_id: Optional[str] = None,
        sync_kind=None,
    ) -> Document:
        # TODO only txt is supported for now
        return BaseDocument(
            uri=doc_uri,
            source=source,
            version=version,
            language_id=language_id,
            sync_kind=sync_kind
        )


class TextLSPWorkspace(Workspace):

    def _create_document(
        self,
        doc_uri: str,
        source: Optional[str] = None,
        version: Optional[int] = None,
        language_id: Optional[str] = None,
    ) -> Document:
        return DocumentTypeFactory.get_document(
            doc_uri=doc_uri,
            source=source,
            version=version,
            language_id=language_id,
            sync_kind=self._sync_kind
        )

    @staticmethod
    def workspace2textlspworkspace(workspace: Workspace):
        return TextLSPWorkspace(
            workspace._root_uri,
            workspace._sync_kind,
            [folder for folder in workspace._folders.values()],
        )
