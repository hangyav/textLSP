import logging

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
        CompletionParams,
        CompletionList,
)

from ..documents.document import BaseDocument, ChangeTracker
from ..utils import merge_dicts
from ..types import (
    Interval,
    TextLSPCodeActionKind,
    ProgressBar,
    PositionDict,
)


logger = logging.getLogger(__name__)


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
        self._progressbar_token = ProgressBar.create_token()

    def _did_open(self, doc: Document):
        raise NotImplementedError()

    def did_open(self, params: DidOpenTextDocumentParams):
        doc = self.get_document(params)
        self.init_document_items(doc)
        self._content_change_dict[doc.uri] = ChangeTracker(doc, True)
        if self.should_run_on(Analyser.CONFIGURATION_CHECK_ON_OPEN):
            with ProgressBar(
                    self.language_server,
                    f'{self.name} checking',
                    token=self._progressbar_token
            ):
                self._did_open(doc)
                self._checked_documents.add(doc.uri)

    def _did_change(self, doc: Document, changes: List[Interval]):
        raise NotImplementedError()

    def _handle_line_shifts(self, params: DidChangeTextDocumentParams):
        # FIXME: this method is very complex, try to make it easier to read
        should_update_diagnostics = False
        doc = self.get_document(params)

        val = 0
        accumulative_shifts = list()
        # handling inline shifts and building a list of line shifts for later
        for change in params.content_changes:
            if type(change) == TextDocumentContentChangeEvent_Type2:
                continue

            if change.range.start != change.range.end:
                tmp_range = Range(
                    start=Position(
                        line=change.range.start.line-val,
                        character=change.range.start.character,
                    ),
                    end=Position(
                        line=change.range.end.line-val,
                        character=change.range.start.character,
                    ),
                )
                num = self.remove_code_items_at_rage(doc, tmp_range, (True, False))
                should_update_diagnostics = should_update_diagnostics or num > 0

            change_text_len = len(change.text)
            line_diff = change.range.end.line - change.range.start.line
            diff = change.text.count('\n') - line_diff
            if diff == 0:
                in_line_diff = change.range.start.character - change.range.end.character
                in_line_diff += change_text_len
                if in_line_diff != 0:
                    # in only some edit in a given line, let's shift the items
                    # in the line
                    next_pos = Position(
                        line=change.range.start.line+1,
                        character=0,
                    )

                    for diag in list(
                        self._diagnostics_dict[doc.uri].irange_values(
                            minimum=change.range.start,
                            maximum=next_pos,
                            inclusive=(True, False)
                        )
                    ):
                        item_range = diag.range
                        diag.range = Range(
                            start=Position(
                                line=item_range.start.line,
                                character=item_range.start.character+in_line_diff
                            ),
                            end=Position(
                                line=item_range.end.line,
                                character=item_range.end.character +
                                (in_line_diff if item_range.start.line ==
                                 item_range.end.line else 0)
                            )
                        )
                        self._diagnostics_dict[doc.uri].update(
                            item_range.start,
                            diag.range.start,
                            diag
                        )
                        should_update_diagnostics = True

                    for action in list(
                            self._code_actions_dict[doc.uri].irange_values(
                                minimum=change.range.start,
                                maximum=next_pos,
                                inclusive=(True, False)
                            )
                    ):
                        item_range = action.edit.document_changes[0].edits[0].range
                        action.edit.document_changes[0].edits[0].range = Range(
                            start=Position(
                                line=item_range.start.line,
                                character=item_range.start.character+in_line_diff
                            ),
                            end=Position(
                                line=item_range.end.line,
                                character=item_range.end.character +
                                (in_line_diff if item_range.start.line ==
                                 item_range.end.line else 0)
                            )
                        )
                        self._code_actions_dict[doc.uri].update(
                            item_range.start,
                            action.edit.document_changes[0].edits[0].range.start,
                            action
                        )
            else:
                # There is a line shift: diff > 0
                val += diff
                accumulative_shifts.append((change.range.start, val, change))
        pos = doc.last_position(True)
        pos = Position(
            line=pos.line - (accumulative_shifts[-1][1] if len(accumulative_shifts) else 0) + 1,
            character=0
        )
        accumulative_shifts.append((pos, val))

        if len(accumulative_shifts) == 0:
            return should_update_diagnostics

        # handling line shifts ############################################
        for idx in range(len(accumulative_shifts)-1):
            pos = accumulative_shifts[idx][0]
            next_pos = accumulative_shifts[idx+1][0]
            shift = accumulative_shifts[idx][1]

            for diag in list(
                    self._diagnostics_dict[doc.uri].irange_values(
                        minimum=pos,
                        maximum=next_pos,
                        inclusive=(True, False)
                    )
            ):
                item_range = diag.range
                char_shift = 0
                if item_range.start.line == pos.line:
                    char_shift = item_range.start.character - \
                        (pos.character + len(accumulative_shifts[idx][2].text))
                diag.range = Range(
                    start=Position(
                        line=item_range.start.line + shift,
                        character=item_range.start.character - char_shift
                    ),
                    end=Position(
                        line=item_range.end.line + shift,
                        character=item_range.end.character -
                        (char_shift if item_range.start.line ==
                         item_range.end.line else 0)
                    )
                )
                self._diagnostics_dict[doc.uri].update(
                    item_range.start,
                    diag.range.start,
                    diag
                )
                should_update_diagnostics = True

            for action in list(
                    self._code_actions_dict[doc.uri].irange_values(
                        minimum=pos,
                        maximum=next_pos,
                        inclusive=(True, False)
                    )
            ):
                item_range = action.edit.document_changes[0].edits[0].range
                char_shift = 0
                if item_range.start.line == pos.line:
                    char_shift = item_range.start.character - \
                        (pos.character + len(accumulative_shifts[idx][2].text))
                action.edit.document_changes[0].edits[0].range = Range(
                    start=Position(
                        line=item_range.start.line + shift,
                        character=item_range.start.character - char_shift
                    ),
                    end=Position(
                        line=item_range.end.line + shift,
                        character=item_range.end.character -
                        (char_shift if item_range.start.line ==
                         item_range.end.line else 0)
                    )
                )
                self._code_actions_dict[doc.uri].update(
                    item_range.start,
                    action.edit.document_changes[0].edits[0].range.start,
                    action
                )

        return should_update_diagnostics

    def _remove_overflown_code_items(self, doc: BaseDocument):
        last_position = doc.last_position(True)

        self._diagnostics_dict[doc.uri].remove_from(last_position, False)
        self._code_actions_dict[doc.uri].remove_from(last_position, False)

    def _handle_shifts(self, params: DidChangeTextDocumentParams):
        """
        Handlines line shifts and position shifts within lines
        """
        doc = self.get_document(params)
        should_update_diagnostics = self._handle_line_shifts(params)
        self._remove_overflown_code_items(doc)

        return should_update_diagnostics

    def _update_single_code_action(self, action: CodeAction, doc: BaseDocument):
        # update document version
        if action.edit is not None:
            for change in action.edit.document_changes:
                change.text_document = VersionedTextDocumentIdentifier(
                    uri=doc.uri,
                    version=doc.version,
                )

    def _update_code_actions(self, doc: BaseDocument):
        """
        Updates the document version of code actions
        """
        for action in self._code_actions_dict[doc.uri]:
            self._update_single_code_action(
                action,
                doc,
            )

    def did_change(self, params: DidChangeTextDocumentParams):
        doc = self.get_document(params)
        should_update_diagnostics = self._handle_shifts(params)
        self._update_code_actions(doc)

        if self.should_run_on(Analyser.CONFIGURATION_CHECK_ON_CHANGE):
            if self._content_change_dict[doc.uri].full_document_change:
                self.did_open(
                    DidOpenTextDocumentParams(params.text_document)
                )
            else:
                changes = self._content_change_dict[doc.uri].get_changes()
                self._content_change_dict[doc.uri] = ChangeTracker(doc, True)
                with ProgressBar(
                        self.language_server,
                        f'{self.name} checking',
                        token=self._progressbar_token
                ):
                    self._did_change(doc, changes)
        elif should_update_diagnostics:
            self.language_server.publish_stored_diagnostics(doc)

    def update_document(self, doc: Document, change: TextDocumentContentChangeEvent):
        self._content_change_dict[doc.uri].update_document(change, doc)

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
                    self._content_change_dict[doc.uri] = ChangeTracker(doc, True)
                    with ProgressBar(
                            self.language_server,
                            f'{self.name} checking',
                            token=self._progressbar_token
                    ):
                        self._did_change(doc, changes)

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
        self._diagnostics_dict[doc.uri] = PositionDict()

    def get_diagnostics(self, doc: Document):
        return self._diagnostics_dict.get(doc.uri, PositionDict())

    def add_diagnostics(self, doc: Document, diagnostics: List[Diagnostic]):
        for diag in diagnostics:
            self._diagnostics_dict[doc.uri].add(diag.range.start, diag)
        self.language_server.publish_stored_diagnostics(doc)

    def remove_code_items_at_rage(self, doc: Document, pos_range: Range, inclusive=(True, True)):
        num = 0
        num += self._diagnostics_dict[doc.uri].remove_between(pos_range, inclusive)
        num += self._code_actions_dict[doc.uri].remove_between(pos_range, inclusive)
        return num

    def init_code_actions(self, doc: Document):
        self._code_actions_dict[doc.uri] = PositionDict()

    def get_code_actions(self, params: CodeActionParams) -> Optional[List[CodeAction]]:
        doc = self.get_document(params)
        range = params.range

        # TODO make this faster?
        res = [
            action
            for action in self._code_actions_dict[doc.uri].irange_values(maximum=range.start)
            if (
                (
                    # action.edit.document_changes[0].edits[0].range.start <= range.start
                    # and
                    action.edit.document_changes[0].edits[0].range.end >= range.end
                )
                # if it's not reachable by the cursor
                or (
                    action.edit.document_changes[0].edits[0].range.start.line == range.start.line
                    and len(
                        doc.lines[range.start.line].strip()
                    ) <= action.edit.document_changes[0].edits[0].range.start.character
                )
            )
        ]

        if not (
            self.should_run_on(self.CONFIGURATION_CHECK_ON_CHANGE)
            or self.should_run_on(self.CONFIGURATION_CHECK_ON_SAVE)
        ):
            if range.start != range.end:
                paragraphs = doc.paragraphs_at_range(range, True)
            else:
                paragraphs = [doc.paragraph_at_position(range.start, True)]

            num_paragraphs = len(paragraphs)
            if num_paragraphs > 0:
                if num_paragraphs == 1:
                    title = f'Run {self.name} on paragraph'
                    paragraph = paragraphs[0]
                else:
                    title = f'Run {self.name} on the selected paragraphs'
                    paragraph = Interval(
                        start=paragraphs[0].start,
                        length=paragraphs[-1].start + paragraphs[-1].length - paragraphs[0].start,
                    )

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
        for action in actions:
            self._code_actions_dict[doc.uri].add(
                action.edit.document_changes[0].edits[0].range.start,
                action,
            )

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
            with ProgressBar(
                    self.language_server,
                    f'{self.name} checking',
                    token=self._progressbar_token
            ):
                self._command_analyse(doc, interval)
        else:
            with ProgressBar(
                    self.language_server,
                    f'{self.name} checking',
                    token=self._progressbar_token
            ):
                self._command_analyse(doc)
            self._checked_documents.add(args['uri'])

    def get_completions(self, params: Optional[CompletionParams] = None) -> Optional[CompletionList]:
        return None


class AnalysisError(Exception):
    pass
