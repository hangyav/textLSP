import sys
import inspect
import importlib
import logging
import asyncio

from lsprotocol.types import MessageType
from lsprotocol.types import (
        DidOpenTextDocumentParams,
        DidChangeTextDocumentParams,
        DidCloseTextDocumentParams,
)
from pygls.server import LanguageServer

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
            if not config.setdefault('enabled', True):
                continue
            if name in old_analysers:
                analyser = old_analysers[name]
                analyser.update_settings(config)
                self.analysers[name] = analyser
            else:
                cls = self._get_analyser_class(name)
                if cls is not None:
                    self.analysers[name] = cls(self.language_server, config)

        for name, analyser in old_analysers.items():
            if name not in self.analysers:
                analyser.close()

    def _get_analyser_class(self, name):
        try:
            module = importlib.import_module('{}.{}'.format(
                analysers.__name__,
                name
            ))
        except ModuleNotFoundError:
            self.language_server.show_message(
                f'Unsupported analyser: {name}',
                MessageType.Error,
            )
            return None

        cls = None
        for cls_name, obj in inspect.getmembers(
                sys.modules[module.__name__],
                inspect.isclass
        ):
            if issubclass(obj, Analyser):
                if cls is None:
                    cls = obj
                else:
                    self.language_server.show_message(
                        f'There are multiple implementations of {name}. We use'
                        'the first one. This is an implementation error.'
                        'Please report this issue!',
                        MessageType.Error,
                    )
                    break

        if cls is None:
            self.language_server.show_message(
                f'There is no implementation of {name}. We use the first one.'
                'This is an implementation error. Please report this issue!',
                MessageType.Error,
            )

        return cls

    async def _submit_task(self, function, *args, **kwargs):
        functions = list()
        for name, analyser in self.analysers.items():
            functions.append(
                self.language_server.loop.create_task(
                    function(name, analyser, *args, **kwargs)
                )
            )

        if len(functions) == 0:
            return

        await asyncio.wait(functions)

    async def _did_open(
        self,
        analyser_name: str,
        analyser: Analyser,
        params: DidOpenTextDocumentParams,
    ):
        analyser.did_open(
            params,
        )

    async def did_open(self, params: DidOpenTextDocumentParams):
        await self._submit_task(
            self._did_open,
            params=params
        )

    async def _did_change(
        self,
        analyser_name: str,
        analyser: Analyser,
        params: DidChangeTextDocumentParams,
    ):
        analyser.did_change(
            params,
        )

    async def did_change(self, params: DidChangeTextDocumentParams):
        await self._submit_task(
            self._did_change,
            params=params
        )

    async def _did_close(
        self,
        analyser_name: str,
        analyser: Analyser,
        params: DidCloseTextDocumentParams
    ):
        analyser.did_close(
            params,
        )

    async def did_close(self, params: DidCloseTextDocumentParams):
        await self._submit_task(
            self._did_close,
            params=params
        )
