import logging

from typing import Optional

from pygls.workspace import Workspace, Document
from pygls.lsp.types import NumType

logger = logging.getLogger(__name__)


class BaseDocument(Document):
    @property
    def cleaned_source(self):
        return self.source

    @property
    def language(self):
        return 'en'


class DocumentTypeFactory():
    @staticmethod
    def get_document(
        doc_uri: str,
        source: Optional[str] = None,
        version: Optional[NumType] = None,
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
        version: Optional[NumType] = None,
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
