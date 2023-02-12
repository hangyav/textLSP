import logging
import asyncio

from typing import List, Optional
from lsprotocol.types import MessageType
from lsprotocol.types import (
        DidOpenTextDocumentParams,
        DidChangeTextDocumentParams,
        DidCloseTextDocumentParams,
        DidSaveTextDocumentParams,
        TextDocumentContentChangeEvent,
        CodeActionParams,
        CodeAction,
        CompletionParams,
        CompletionList,
)
from pygls.workspace import Document

from .. import analysers
from .analyser import Analyser, AnalysisError
from ..utils import get_class
from ..types import ConfigurationError


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
            if not config.setdefault('enabled', False):
                continue
            if name in old_analysers:
                analyser = old_analysers[name]
                analyser.update_settings(config)
                self.analysers[name] = analyser
            else:
                try:
                    cls = get_class(
                        '{}.{}'.format(analysers.__name__, name),
                        Analyser,
                    )
                    self.analysers[name] = cls(
                        self.language_server,
                        config,
                        name
                    )
                except ImportError as e:
                    self.language_server.show_message(
                        str(e),
                        MessageType.Error,
                    )
                except ConfigurationError as e:
                    self.language_server.show_message(
                        str(e),
                        MessageType.Error,
                    )

        for name, analyser in old_analysers.items():
            if name not in self.analysers:
                analyser.close()

    def get_diagnostics(self, doc: Document):
        return [analyser.get_diagnostics(doc) for analyser in self.analysers.values()]

    def get_code_actions(self, params: CodeActionParams) -> Optional[List[CodeAction]]:
        res = list()
        for analyser in self.analysers.values():
            tmp_lst = analyser.get_code_actions(params)
            if tmp_lst is not None and len(tmp_lst) > 0:
                res.extend(tmp_lst)

        return res if len(res) > 0 else None

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
        try:
            analyser.did_open(
                params,
            )
        except AnalysisError as e:
            self.language_server.show_message(
                str(f'{analyser_name}: {e}'),
                MessageType.Error,
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
        try:
            analyser.did_change(
                params,
            )
        except AnalysisError as e:
            self.language_server.show_message(
                str(f'{analyser_name}: {e}'),
                MessageType.Error,
            )

    async def did_change(self, params: DidChangeTextDocumentParams):
        await self._submit_task(
            self._did_change,
            params=params
        )

    async def _did_save(
        self,
        analyser_name: str,
        analyser: Analyser,
        params: DidSaveTextDocumentParams,
    ):
        try:
            analyser.did_save(
                params,
            )
        except AnalysisError as e:
            self.language_server.show_message(
                str(f'{analyser_name}: {e}'),
                MessageType.Error,
            )

    async def did_save(self, params: DidSaveTextDocumentParams):
        await self._submit_task(
            self._did_save,
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

    async def _command_analyse(
        self,
        analyser_name: str,
        analyser: Analyser,
        args,
    ):
        try:
            analyser.command_analyse(*args)
        except AnalysisError as e:
            self.language_server.show_message(
                str(f'{analyser_name}: {e}'),
                MessageType.Error,
            )

    async def command_analyse(self, *args):
        args = args[0]
        if 'analyser' in args[0]:
            analyser_name = args[0].pop('analyser')
            analyser = self.analysers[analyser_name]
            try:
                analyser.command_analyse(*args)
            except AnalysisError as e:
                self.language_server.show_message(
                    str(f'{analyser_name}: {e}'),
                    MessageType.Error,
                )
        else:
            await self._submit_task(self._command_analyse, args)

    async def command_custom_command(self, *args):
        args = args[0][0]
        assert 'analyser' in args
        analyser = self.analysers[args.pop('analyser')]
        command = args.pop('command')
        ext_command = f'command_{command}'

        if hasattr(analyser, ext_command):
            getattr(analyser, ext_command)(**args)
        else:
            self.language_server.show_message(
                str(f'No custom command supported by {analyser}: {command}'),
                MessageType.Error,
            )

    def update_document(self, doc: Document, change: TextDocumentContentChangeEvent):
        for name, analyser in self.analysers.items():
            analyser.update_document(doc, change)

    def get_completions(self, params: Optional[CompletionParams] = None) -> CompletionList:
        comp_lst = list()
        for _, analyser in self.analysers.items():
            tmp = analyser.get_completions(params)
            if tmp is not None and len(tmp) > 0:
                comp_lst.extend(tmp)

        return CompletionList(
            is_incomplete=False,
            items=comp_lst,
        )
