import sys
import inspect
import importlib
import logging

from lsprotocol.types import MessageType

from .. import analysers
from .analyser import Analyser


logger = logging.getLogger(__name__)


class AnalyserHandler():

    def __init__(self, language_server, settings=None):
        self.language_server = language_server
        self.analysers = dict()
        self.update_settings(settings)

    def update_settings(self, settings):
        if settings is None:
            return

        old_analysers = self.analysers
        self.analysers = dict()
        for name, config in settings.items():
            if name in old_analysers:
                analyser = old_analysers[name]
                analyser.update_settings(config)
                self.analysers[name] = analyser
            else:
                cls = self._get_analyser_class(name)
                if cls is not None:
                    self.analysers[name] = cls(config)

        for name, analyser in old_analysers.items():
            if name not in self.analysers:
                analyser.close()

    def _get_analyser_class(self, name):
        try:
            module = importlib.import_module('{}.{}'.format(analysers.__name__, name))
        except ModuleNotFoundError:
            self.language_server.show_message(
                f'Unsupported analyser: {name}',
                MessageType.Error,
            )
            return None

        cls = None
        for cls_name, obj in inspect.getmembers(sys.modules[module.__name__], inspect.isclass):
            if issubclass(obj, Analyser):
                if cls is None:
                    cls = obj
                else:
                    self.language_server.show_message(
                        f'There are multiple implementations of {name}. We use the first one. This is an implementatn error. Please report this issue!',
                        MessageType.Error,
                    )
                    break

        if cls is None:
            self.language_server.show_message(
                f'There is no implementation of {name}. We use the first one. This is an implementation erro. Please report this issue!',
                MessageType.Error,
            )

        return cls
