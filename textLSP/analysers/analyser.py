import bisect

from typing import List, Optional
from pygls.server import LanguageServer
from pygls.workspace import Document
from lsprotocol.types import (
        DidOpenTextDocumentParams,
        DidChangeTextDocumentParams,
        DidCloseTextDocumentParams,
        DidSaveTextDocumentParams,
        TextDocumentContentChangeEvent,
        TextDocumentContentChangeEvent_Type2,
        Diagnostic,
        DiagnosticSeverity,
        Range,
        Position,
        CodeActionParams,
        CodeAction,
        WorkspaceEdit,
        TextDocumentEdit,
        TextEdit,
        Command,
        VersionedTextDocumentIdentifier,
        MessageType,
        CompletionParams,
        CompletionList,
)

from ..documents.document import BaseDocument, ChangeTracker
from ..utils import merge_dicts
from ..types import Interval, TextLSPCodeActionKind


class Analyser():
    CONFIGURATION_SEVERITY = 'severity'
    CONFIGURATION_CHECK = 'check_text'
    CONFIGURATION_CHECK_ON_OPEN = 'on_open'
    CONFIGURATION_CHECK_ON_CHANGE = 'on_change'
    CONFIGURATION_CHECK_ON_SAVE = 'on_save'

    SETTINGS_DEFAULT_CHECK_ON = {
        CONFIGURATION_CHECK_ON_OPEN: True,
        CONFIGURATION_CHECK_ON_CHANGE: False,
        CONFIGURATION_CHECK_ON_SAVE: True,
    }

    def __init__(self, language_server: LanguageServer, config: dict, name: str):
        self.name = name
        self.default_severity = DiagnosticSeverity.Information
        self.language_server = language_server
        self.config = dict()
        self.update_settings(config)
        self._diagnostics_dict = dict()
        self._code_actions_dict = dict()
        self._content_change_dict = dict()
        self._checked_documents = set()

    def _did_open(self, doc: Document):
        raise NotImplementedError()

    def did_open(self, params: DidOpenTextDocumentParams):
        doc = self.get_document(params)
        self.init_document_items(doc)
        self._content_change_dict[doc.uri] = ChangeTracker(doc, True)
        if self.should_run_on(Analyser.CONFIGURATION_CHECK_ON_OPEN):
            self._did_open(doc)
            self._checked_documents.add(doc.uri)

    def _did_change(self, doc: Document, changes: List[Interval]):
        raise NotImplementedError()

    def _get_line_shifts(self, params: DidChangeTextDocumentParams) -> List:
        res = list()
        for change in params.content_changes:
            if type(change) == TextDocumentContentChangeEvent_Type2:
                continue

            line_diff = change.range.end.line - change.range.start.line
            diff = change.text.count('\n') - line_diff
            if diff != 0:
                res.append((change.range.start.line, diff))

        return res

    def _handle_line_shifts(self, doc: BaseDocument, line_shifts: List):
        """
        params: line_shifts: List of tuples (line, shift) should be sorted
        """
        if len(line_shifts) == 0:
            return

        val = 0
        bisect_lst = [line_shifts[0][0]]
        accumulative_shifts = [(line_shifts[0][0], 0)]
        for shift in line_shifts:
            val += shift[1]
            accumulative_shifts.append((shift[0]+1, val))
            bisect_lst.append(shift[0]+1)
        num_shifts = len(accumulative_shifts)

        # TODO extract to function
        # diagnostics
        diagnostics = list()
        for diag in self._diagnostics_dict[doc.uri]:
            range = diag.range
            idx = bisect.bisect_left(bisect_lst, range.start.line)
            idx = min(idx, num_shifts-1)
            shift = accumulative_shifts[idx][1]

            if shift != 0:
                if range.start.line + shift < 0:
                    continue
                diag.range = Range(
                    start=Position(
                        line=range.start.line + shift,
                        character=range.start.character
                    ),
                    end=Position(
                        line=range.end.line + shift,
                        character=range.end.character
                    )
                )
            diagnostics.append(diag)
        self._diagnostics_dict[doc.uri] = diagnostics

        # code actions
        code_actions = list()
        for action in self._code_actions_dict[doc.uri]:
            range = action.edit.document_changes[0].edits[0].range
            idx = bisect.bisect_left(bisect_lst, range.start.line)
            idx = min(idx, num_shifts-1)
            shift = accumulative_shifts[idx][1]

            if shift != 0:
                if range.start.line + shift < 0:
                    continue
                action.edit.document_changes[0].edits[0].range = Range(
                    start=Position(
                        line=range.start.line + shift,
                        character=range.start.character
                    ),
                    end=Position(
                        line=range.end.line + shift,
                        character=range.end.character
                    )
                )
            code_actions.append(action)
        self._code_actions_dict[doc.uri] = code_actions

    def _remove_overflown_code_items(self, doc: BaseDocument):
        last_position = doc.last_position(True)

        self._diagnostics_dict[doc.uri] = [
            diag
            for diag in self._diagnostics_dict[doc.uri]
            if diag.range.start <= last_position
        ]

        self._code_actions_dict[doc.uri] = [
            action
            for action in self._code_actions_dict[doc.uri]
            if action.edit.document_changes[0].edits[0].range.start <= last_position
        ]

    def did_change(self, params: DidChangeTextDocumentParams):
        # TODO handle shifts within lines
        line_shifts = self._get_line_shifts(params)
        doc = self.get_document(params)
        self._handle_line_shifts(doc, line_shifts)
        self._remove_overflown_code_items(doc)

        if self.should_run_on(Analyser.CONFIGURATION_CHECK_ON_CHANGE):
            if self._content_change_dict[doc.uri].full_document_change:
                self.did_open(
                    DidOpenTextDocumentParams(params.text_document)
                )
            else:
                changes = self._content_change_dict[doc.uri].get_changes()
                self._did_change(doc, changes)
                self._content_change_dict[doc.uri] = ChangeTracker(doc, True)
        elif len(line_shifts) > 0:
            self.language_server.publish_stored_diagnostics(doc)

    def update_document(self, doc: Document, change: TextDocumentContentChangeEvent):
        self._content_change_dict[doc.uri].update_document(change)

    def did_save(self, params: DidSaveTextDocumentParams):
        if self.should_run_on(Analyser.CONFIGURATION_CHECK_ON_SAVE):
            doc = self.get_document(params)

            if len(self._content_change_dict[doc.uri]) > 0:
                if self._content_change_dict[doc.uri].full_document_change:
                    self.did_open(
                        DidOpenTextDocumentParams(params.text_document)
                    )
                else:
                    changes = self._content_change_dict[doc.uri].get_changes()
                    self._did_change(doc, changes)
                    self._content_change_dict[doc.uri] = ChangeTracker(doc, True)

    def _did_close(self, doc: Document):
        pass

    def did_close(self, params: DidCloseTextDocumentParams):
        self._did_close(self.get_document(params))

    def update_settings(self, settings):
        self.config = merge_dicts(self.config, settings)

    def close(self):
        pass

    def get_document(self, document_descriptor) -> BaseDocument:
        if type(document_descriptor) != str:
            document_descriptor = document_descriptor.text_document.uri
        return self.language_server.workspace.get_document(document_descriptor)

    def get_severity(self) -> DiagnosticSeverity:
        if Analyser.CONFIGURATION_SEVERITY in self.config:
            try:
                return DiagnosticSeverity[self.config[Analyser.CONFIGURATION_SEVERITY]]
            except KeyError:
                pass
        return self.default_severity

    def should_run_on(self, event: str) -> bool:
        return self.config.setdefault(
                Analyser.CONFIGURATION_CHECK,
                dict()
        ).setdefault(
            event,
            Analyser.SETTINGS_DEFAULT_CHECK_ON.setdefault(
                event,
                False,
            )
        )

    def init_diagnostics(self, doc: Document):
        self._diagnostics_dict[doc.uri] = list()

    def get_diagnostics(self, doc: Document):
        return self._diagnostics_dict.get(doc.uri, list())

    def add_diagnostics(self, doc: Document, diagnostics: List[Diagnostic]):
        self._diagnostics_dict[doc.uri] += diagnostics
        self.language_server.publish_stored_diagnostics(doc)

    def remove_code_items_at_rage(self, doc: Document, pos_range: Range):
        diagnostics = list()
        for diag in self.get_diagnostics(doc):
            if diag.range.end < pos_range.start or diag.range.start > pos_range.end:
                diagnostics.append(diag)
        self._diagnostics_dict[doc.uri] = diagnostics

        code_actions = list()
        for action in self._code_actions_dict[doc.uri]:
            range = action.edit.document_changes[0].edits[0].range
            if range.end < pos_range.start or range.start > pos_range.end:
                code_actions.append(action)
        self._code_actions_dict[doc.uri] = code_actions

    def init_code_actions(self, doc: Document):
        self._code_actions_dict[doc.uri] = list()

    def get_code_actions(self, params: CodeActionParams) -> Optional[List[CodeAction]]:
        doc = self.get_document(params)
        range = params.range
        if range.start != range.end:
            self.language_server.show_message(
                'Code action is not supported for range.',
                MessageType.Error,
            )
            return None

        # TODO make this faster?
        res = [
            action
            for action in self._code_actions_dict[doc.uri]
            if (
                (
                    action.edit.document_changes[0].edits[0].range.start <= range.start
                    and action.edit.document_changes[0].edits[0].range.end >= range.end
                )
                # if it's not reachable by the cursor
                or (
                    action.edit.document_changes[0].edits[0].range.start.line == range.start.line
                    and len(
                        doc.lines[range.start.line]
                    ) <= action.edit.document_changes[0].edits[0].range.start.character
                )
            )
        ]

        if not (
            self.should_run_on(self.CONFIGURATION_CHECK_ON_CHANGE)
            or self.should_run_on(self.CONFIGURATION_CHECK_ON_SAVE)
        ):
            title = f'Run {self.name} on paragraph'
            paragraph = doc.paragraph_at_position(range.start, True)
            res.append(
                self.build_command_action(
                    doc=doc,
                    title=title,
                    command=Command(
                        title=title,
                        command=self.language_server.COMMAND_ANALYSE,
                        arguments=[{
                            'uri': doc.uri,
                            'analyser': self.name,
                            'interval': paragraph,
                        }],
                    ),
                )
            )

        if range.start == Position(0, 0) and doc.uri not in self._checked_documents:
            title = f'Run {self.name} on the full document'
            res.append(
                self.build_command_action(
                    doc=doc,
                    title=title,
                    command=Command(
                        title=title,
                        command=self.language_server.COMMAND_ANALYSE,
                        arguments=[{
                            'uri': doc.uri,
                            'analyser': self.name,
                        }],
                    ),
                )
            )

        return res

    def add_code_actions(self, doc: Document, actions: List[CodeAction]):
        self._code_actions_dict[doc.uri] += actions

    @staticmethod
    def build_single_suggestion_action(
            doc: Document,
            title: str,
            edit: TextEdit,
            kind=TextLSPCodeActionKind.AcceptSuggestion,
            diagnostic: Diagnostic = None,
    ) -> CodeAction:
        return CodeAction(
            title=title,
            kind=kind,
            diagnostics=[diagnostic] if diagnostic else None,
            edit=WorkspaceEdit(
                document_changes=[
                    TextDocumentEdit(
                        text_document=VersionedTextDocumentIdentifier(
                            uri=doc.uri,
                            version=doc.version,
                        ),
                        edits=[edit]
                    )
                ]
            )
        )

    @staticmethod
    def build_command_action(
            doc: Document,
            title: str,
            command: Command,
            kind=TextLSPCodeActionKind.Command,
            diagnostic: Diagnostic = None,
    ) -> CodeAction:
        return CodeAction(
            title=title,
            kind=kind,
            diagnostics=[diagnostic] if diagnostic else None,
            command=command,
        )

    def init_document_items(self, doc: Document):
        self.init_diagnostics(doc)
        self.init_code_actions(doc)

    def _command_analyse(self, doc: BaseDocument, interval: Interval = None):
        if interval is not None:
            self._did_change(doc, [interval])
        else:
            self._did_open(doc)

    def command_analyse(self, *args):
        args = args[0]
        doc = self.get_document(args['uri'])
        if 'interval' in args:
            interval = args['interval']
            interval = Interval(interval['start'], interval['length'])
            self._command_analyse(doc, interval)
        else:
            self._command_analyse(doc)
            self._checked_documents.add(args['uri'])

    def get_completions(self, params: Optional[CompletionParams] = None) -> Optional[CompletionList]:
        return None


class AnalysisError(Exception):
    pass
