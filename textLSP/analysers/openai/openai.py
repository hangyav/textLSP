import logging
from typing import List, Literal, Optional, Tuple

from lsprotocol.types import (
    ApplyWorkspaceEditParams,
    CodeAction,
    CodeActionParams,
    Command,
    CompletionItem,
    CompletionList,
    CompletionParams,
    Diagnostic,
    MessageType,
    Position,
    Range,
    ShowMessageParams,
    TextDocumentEdit,
    TextEdit,
    VersionedTextDocumentIdentifier,
    WorkspaceEdit,
)
from openai import APIError, Omit, OpenAI, omit
from openai.types.shared.reasoning_effort import ReasoningEffort
from pygls.lsp.server import LanguageServer

from ...documents.document import BaseDocument
from ...types import ConfigurationError, Interval, ProgressBar, TokenDiff
from ..analyser import Analyser

logger = logging.getLogger(__name__)


class OpenAIAnalyser(Analyser):
    CONFIGURATION_API_KEY = "api_key"
    CONFIGURATION_URL = "url"
    CONFIGURATION_MODEL = "model"
    CONFIGURATION_EDIT_INSTRUCTION = "edit_instruction"
    CONFIGURATION_TEMPERATURE = "temperature"
    CONFIGURATION_MAX_TOKEN = "max_token"
    CONFIGURATION_SEED = "seed"
    CONFIGURATION_STORE = "store"
    CONFIGURATION_VERBOSITY = "verbosity"
    CONFIGURATION_REASONING_EFFORT = "reasoning_effort"
    CONFIGURATION_PROMPT_MAGIC = "prompt_magic"

    SETTINGS_DEFAULT_URL = None
    SETTINGS_DEFAULT_MODEL = "gpt-5-nano"
    SETTINGS_DEFAULT_EDIT_INSTRUCTION = (
        "Correct all grammar mistakes in the following text."
        " Be rigorous but do not change the meaning and style, or add or remove content."
        " Output only the corrected text even if it is correct."
    )
    SETTINGS_DEFAULT_TEMPERATURE = None
    SETTINGS_DEFAULT_MAX_TOKEN = 100
    SETTINGS_DEFAULT_SEED = 42
    SETTINGS_DEFAULT_STORE = False
    SETTINGS_DEFAULT_VERBOSITY = "medium"
    SETTINGS_DEFAULT_REASONING_EFFORT = "minimal"
    SETTINGS_DEFAULT_PROMPT_MAGIC = "%OPENAI% "
    SETTINGS_DEFAULT_CHECK_ON = {
        Analyser.CONFIGURATION_CHECK_ON_OPEN: False,
        Analyser.CONFIGURATION_CHECK_ON_CHANGE: False,
        Analyser.CONFIGURATION_CHECK_ON_SAVE: False,
    }

    def __init__(self, language_server: LanguageServer, config: dict, name: str):
        super().__init__(language_server, config, name)
        if self.CONFIGURATION_API_KEY not in self.config:
            raise ConfigurationError(
                f"Required parameter: {name}.{self.CONFIGURATION_API_KEY}"
            )

        for key, default in [
            (self.SETTINGS_DEFAULT_TEMPERATURE, self.CONFIGURATION_TEMPERATURE),
            (self.SETTINGS_DEFAULT_MAX_TOKEN, self.CONFIGURATION_MAX_TOKEN),
            (self.SETTINGS_DEFAULT_SEED, self.CONFIGURATION_SEED),
            (self.SETTINGS_DEFAULT_STORE, self.CONFIGURATION_STORE),
            (self.SETTINGS_DEFAULT_VERBOSITY, self.CONFIGURATION_VERBOSITY),
            (
                self.SETTINGS_DEFAULT_REASONING_EFFORT,
                self.CONFIGURATION_REASONING_EFFORT,
            ),
        ]:
            if self.config.get(key, default) is None or self.config.get(key) == "none":
                self.config[key] = omit

        url = self.config.get(self.CONFIGURATION_URL, self.SETTINGS_DEFAULT_URL)
        if url is not None and url.lower() == "none":
            url = None
        self._client = OpenAI(
            api_key=self.config[self.CONFIGURATION_API_KEY],
            base_url=url,
        )

    def _chat_endpoint(
        self,
        system_msg: str,
        user_msg: str,
        model: str,
        temperature: Optional[float] | Omit = omit,
        max_tokens: Optional[int] | Omit = omit,
        seed: Optional[int] | Omit = omit,
        store: Optional[bool] | Omit = omit,
        verbosity: Optional[Literal["low", "medium", "high"]] | Omit = omit,
        reasoning_effort: Optional[ReasoningEffort] | Omit = omit,
    ):
        assert system_msg is not None or user_msg is not None

        messages = list()
        if system_msg is not None:
            messages.append({"role": "system", "content": system_msg}),
        if user_msg is not None:
            messages.append({"role": "user", "content": user_msg}),

        logger.debug(f"Input messages: {messages}")
        res = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_tokens,
            seed=seed,
            store=store,
            verbosity=verbosity,
            reasoning_effort=reasoning_effort,
        )
        logger.debug(f"Response: {res}")

        return res

    def _edit(self, text) -> List[TokenDiff]:
        res = self._chat_endpoint(
            system_msg=self.config.get(
                self.CONFIGURATION_EDIT_INSTRUCTION,
                self.SETTINGS_DEFAULT_EDIT_INSTRUCTION,
            ),
            user_msg=text,
            model=self.config.get(
                self.CONFIGURATION_MODEL, self.SETTINGS_DEFAULT_MODEL
            ),
            temperature=self.config.get(
                self.CONFIGURATION_TEMPERATURE, self.SETTINGS_DEFAULT_TEMPERATURE
            ),
            seed=self.config.get(self.CONFIGURATION_SEED, self.SETTINGS_DEFAULT_SEED),
            store=self.config.get(
                self.CONFIGURATION_STORE, self.SETTINGS_DEFAULT_STORE
            ),
            verbosity=self.config.get(
                self.CONFIGURATION_VERBOSITY, self.SETTINGS_DEFAULT_VERBOSITY
            ),
            reasoning_effort=self.config.get(
                self.CONFIGURATION_REASONING_EFFORT,
                self.SETTINGS_DEFAULT_REASONING_EFFORT,
            ),
        )

        if len(res.choices) > 0:
            res_text = (
                res.choices[0].message.content.strip()
            )
            return TokenDiff.token_level_diff(text, res_text)

        return []

    def _generate(self, text) -> Optional[str]:
        res = self._chat_endpoint(
            user_msg=text,
            system_msg=None,
            model=self.config.get(
                self.CONFIGURATION_MODEL, self.SETTINGS_DEFAULT_MODEL
            ),
            temperature=self.config.get(
                self.CONFIGURATION_TEMPERATURE, self.SETTINGS_DEFAULT_TEMPERATURE
            ),
            max_tokens=self.config.get(
                self.CONFIGURATION_MAX_TOKEN, self.SETTINGS_DEFAULT_MAX_TOKEN
            ),
            seed=self.config.get(self.CONFIGURATION_SEED, self.SETTINGS_DEFAULT_SEED),
            store=self.config.get(
                self.CONFIGURATION_STORE, self.SETTINGS_DEFAULT_STORE
            ),
            verbosity=self.config.get(
                self.CONFIGURATION_VERBOSITY, self.SETTINGS_DEFAULT_VERBOSITY
            ),
            reasoning_effort=self.config.get(
                self.CONFIGURATION_REASONING_EFFORT,
                self.SETTINGS_DEFAULT_REASONING_EFFORT,
            ),
        )

        if len(res.choices) > 0:
            # the API escapes special characters such as newlines
            return (
                res.choices[0].message.content.strip()
            )

        return None

    def _analyse(
        self, text, doc, offset=0
    ) -> Tuple[List[Diagnostic], List[CodeAction]]:
        diagnostics = list()
        code_actions = list()

        # we don not want trailing whitespace
        text = text.rstrip()

        try:
            edits = self._edit(text)
        except APIError as e:
            self.language_server.window_show_message(
                ShowMessageParams(
                    message=str(e),
                    type=MessageType.Error,
                )
            )
            edits = []

        for edit in edits:
            if edit.type == TokenDiff.INSERT:
                if edit.offset >= len(text):
                    edit.new_token = f" {edit.new_token}"
                else:
                    edit.new_token = f" {edit.new_token} "
                    edit.old_token = " "
                    edit.offset -= 1
                    edit.length += 1

            token = edit.old_token

            range = doc.range_at_offset(edit.offset + offset, edit.length, True)
            range = Range(
                start=range.start,
                end=Position(
                    line=range.end.line,
                    character=range.end.character + 1,
                ),
            )

            if edit.type == TokenDiff.INSERT:
                message = f'insert "{edit.new_token}"'
            elif edit.type == TokenDiff.REPLACE:
                message = f'"{token}": use "{edit.new_token}" instead'
            else:
                message = f'"{token}": remove'

            diagnostic = Diagnostic(
                range=range,
                message=message,
                source="openai",
                severity=self.get_severity(),
                code=f"openai:{edit.type}",
            )
            action = self.build_single_suggestion_action(
                doc=doc,
                title=f'"{token}" -> "{edit.new_token}"',
                edit=TextEdit(
                    range=diagnostic.range,
                    new_text=edit.new_token,
                ),
                diagnostic=diagnostic,
            )
            code_actions.append(action)
            diagnostics.append(diagnostic)

        return diagnostics, code_actions

    def _did_open(self, doc: BaseDocument):
        diagnostics = list()
        code_actions = list()
        checked = set()
        for paragraph in doc.paragraphs_at_offset(
            0, len(doc.cleaned_source), cleaned=True
        ):
            diags, actions = self._handle_paragraph(doc, paragraph)
            diagnostics.extend(diags)
            code_actions.extend(actions)
            checked.add(paragraph)

        self.add_diagnostics(doc, diagnostics)
        self.add_code_actions(doc, code_actions)

    def _did_change(self, doc: BaseDocument, changes: List[Interval]):
        diagnostics = list()
        code_actions = list()
        checked = set()
        for change in changes:
            paragraph = doc.paragraph_at_offset(
                change.start,
                min_offset=change.start + change.length - 1,
                cleaned=True,
            )
            if paragraph in checked:
                continue

            diags, actions = self._handle_paragraph(doc, paragraph)
            diagnostics.extend(diags)
            code_actions.extend(actions)
            checked.add(paragraph)

        self.add_diagnostics(doc, diagnostics)
        self.add_code_actions(doc, code_actions)

    def _handle_paragraph(self, doc: BaseDocument, paragraph: Interval):
        if (
            len(doc.text_at_offset(paragraph.start, paragraph.length, True).strip())
            == 0
        ):
            return [], []

        pos_range = doc.range_at_offset(paragraph.start, paragraph.length, True)
        self.remove_code_items_at_range(doc, pos_range)

        diags, actions = self._analyse(
            doc.text_at_offset(paragraph.start, paragraph.length, True),
            doc,
            paragraph.start,
        )

        diagnostics = [diag for diag in diags if diag.range.start >= pos_range.start]
        code_actions = [
            action
            for action in actions
            if action.edit.document_changes[0].edits[0].range.start >= pos_range.start
        ]

        return diagnostics, code_actions

    def command_generate(self, uri: str, prompt: str, position: str, new_line=True):
        with ProgressBar(
            self.language_server,
            f"{self.name} generating",
            token=self._progressbar_token,
        ):
            doc = self.get_document(uri)

            try:
                new_text = self._generate(prompt)
            except APIError as e:
                self.language_server.window_show_message(
                    ShowMessageParams(
                        message=str(e),
                        type=MessageType.Error,
                    )
                )
                return

            new_text += "\n"
            position = Position(**eval(position))
            range = Range(
                start=position,
                end=position,
            )

            edit = WorkspaceEdit(
                document_changes=[
                    TextDocumentEdit(
                        text_document=VersionedTextDocumentIdentifier(
                            uri=doc.uri,
                            version=doc.version,
                        ),
                        edits=[
                            TextEdit(
                                range=range,
                                new_text=new_text,
                            ),
                        ],
                    )
                ]
            )
            self.language_server.workspace_apply_edit(
                ApplyWorkspaceEditParams(edit, "textlsp.openai.generate")
            )

    def get_code_actions(self, params: CodeActionParams) -> Optional[List[CodeAction]]:
        doc = self.get_document(params)
        res = super().get_code_actions(params)

        if len(doc.lines) > 0:
            line = doc.lines[params.range.start.line].strip()
        else:
            line = ""
        magic = self.config.get(
            self.CONFIGURATION_PROMPT_MAGIC, self.SETTINGS_DEFAULT_PROMPT_MAGIC
        )
        if magic in line:
            if res is None:
                res = list()

            paragraph = doc.paragraph_at_position(params.range.start, False)
            position = doc.position_at_offset(paragraph.start + paragraph.length, False)
            position = str({"line": position.line, "character": position.character})
            prompt = doc.text_at_offset(paragraph.start, paragraph.length, False)
            prompt = prompt[prompt.find(magic) + len(magic) :]
            title = "Prompt OpenAI"
            res.append(
                self.build_command_action(
                    doc=doc,
                    title=title,
                    command=Command(
                        title=title,
                        command=self.language_server.COMMAND_CUSTOM,
                        arguments=[
                            {
                                "command": "generate",
                                "analyser": self.name,
                                "uri": doc.uri,
                                "prompt": prompt,
                                "position": position,
                                "new_line": True,
                            }
                        ],
                    ),
                )
            )

        return res

    def get_completions(
        self, params: Optional[CompletionParams] = None
    ) -> Optional[CompletionList]:
        if params.position == Position(line=0, character=0):
            return None

        doc = self.get_document(params)
        line = doc.lines[params.position.line]
        magic = self.config.get(
            self.CONFIGURATION_PROMPT_MAGIC, self.SETTINGS_DEFAULT_PROMPT_MAGIC
        )

        line_prefix = line[: params.position.character].strip()
        if len(line_prefix) == 0 or line_prefix in magic:
            return [
                CompletionItem(
                    label=magic,
                    detail="OpenAI magic command for text generation based on"
                    " the prompt that follows.",
                )
            ]
