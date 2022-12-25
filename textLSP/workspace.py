import logging

from typing import Optional

from pygls.workspace import Workspace, Document

from .documents.document import DocumentTypeFactory

logger = logging.getLogger(__name__)


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
