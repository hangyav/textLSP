from pygls.workspace import Workspace
from ..workspace import BaseDocument


class Analyser():
    def did_open(self, document: BaseDocument):
        raise NotImplementedError()

    def did_change(self, document: BaseDocument):
        raise NotImplementedError()

    def did_close(self, workspace: Workspace, document: BaseDocument):
        pass

    def update_settings(self, settings):
        raise NotImplementedError()

    def close(self):
        pass
