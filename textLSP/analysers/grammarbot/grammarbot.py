import logging
import requests
import urllib.parse
import bisect

from typing import List
from lsprotocol.types import (
        Diagnostic,
        TextEdit,
)
from pygls.server import LanguageServer

from ..analyser import Analyser, AnalysisError
from ...documents.document import BaseDocument
from ...utils import batch_text
from ...types import ConfigurationError, TEXT_PASSAGE_PATTERN, Interval


logger = logging.getLogger(__name__)


class GrammarBotAnalyser(Analyser):
    CONFIGURATION_API_KEY = 'api_key'
    CONFIGURATION_INPUT_MAX_REQUESTS = 'input_max_requests'
    CONFIGURATION_REQUESTS_OVERFLOW = 'requests_overflow'

    SETTINGS_DEFAULT_CHECK_ON = {
        Analyser.CONFIGURATION_CHECK_ON_OPEN: False,
        Analyser.CONFIGURATION_CHECK_ON_CHANGE: False,
        Analyser.CONFIGURATION_CHECK_ON_SAVE: False,
    }

    URL = "https://grammarbot.p.rapidapi.com/check"
    CHARACTER_LIMIT_MAX = 8000
    CHARACTER_LIMIT_MIN = 7500
    INPUT_MAX_REQUESTS = 10

    def __init__(self, language_server: LanguageServer, config: dict, name: str):
        super().__init__(language_server, config, name)
        # TODO save this somewhere
        self._remaining_requests = None
        if GrammarBotAnalyser.CONFIGURATION_API_KEY not in self.config:
            raise ConfigurationError('Reqired parameter: grammarbot.api_key')
        self._headers = {
            'content-type': 'application/x-www-form-urlencoded',
            'X-RapidAPI-Key': self.config[GrammarBotAnalyser.CONFIGURATION_API_KEY],
            'X-RapidAPI-Host': 'grammarbot.p.rapidapi.com'
        }

    def _handle_analyses(self, doc: BaseDocument, analyses, text_sections=None):
        diagnostics = list()
        code_actions = list()
        source = doc.cleaned_source
        text_ends = None
        if text_sections is not None:
            text_ends = [section[1] for section in text_sections]

        for match in analyses:
            offset = match['offset']
            length = match['length']
            if text_ends is not None:
                idx = bisect.bisect_left(text_ends, offset)
                if idx == 0:
                    offset = text_sections[idx][0] + offset
                else:
                    offset = text_sections[idx][0] + offset - text_ends[idx-1]

            token = source[offset:offset+length]
            diagnostic = Diagnostic(
                range=doc.range_at_offset(offset, length+1, True),
                message=f'"{token}": {match["message"]}',
                source='grammarbot',
                severity=self.get_severity(),
                code=f'grammarbot:{match["rule"]["id"]}',
            )
            diagnostics.append(diagnostic)
            if len(match['replacements']) > 0:
                for item in match['replacements']:
                    replacement = item['value']
                    action = self.build_single_suggestion_action(
                        doc=doc,
                        title=f'"{token}" -> "{replacement}"',
                        edit=TextEdit(
                            range=diagnostic.range,
                            new_text=replacement,
                        ),
                        diagnostic=diagnostic,
                    )
                    code_actions.append(action)

        return diagnostics, code_actions

    def _did_open(self, doc: BaseDocument):
        diagnostics, code_actions = self._handle_analyses(
            doc,
            self._analyse_text(doc.cleaned_source)
        )
        self.add_diagnostics(doc, diagnostics)
        self.add_code_actions(doc, code_actions)

    def _did_change(self, doc: BaseDocument, changes: List[Interval]):
        text = ''
        # (in_text_start_offset, in_analysis_text_end_offset_inclusive)
        text_sections = list()
        checked = set()

        for change in changes:
            paragraph = doc.paragraph_at_offset(
                change.start,
                min_length=change.length,
                cleaned=True,
            )
            if paragraph in checked:
                continue
            checked.add(paragraph)

            pos_range = doc.range_at_offset(
                paragraph.start,
                paragraph.length,
                True
            )
            self.remove_code_items_at_rage(doc, pos_range)

            paragraph_text = doc.text_at_offset(paragraph.start, paragraph.length)
            text += paragraph_text
            text += '\n'
            text_sections.append((paragraph.start, len(text)))

        diagnostics, code_actions = self._handle_analyses(
            doc,
            self._analyse_text(text),
            text_sections
        )

        self.add_diagnostics(doc, diagnostics)
        self.add_code_actions(doc, code_actions)

    def _analyse_text(self, text):
        spans = list(batch_text(
            text,
            TEXT_PASSAGE_PATTERN,
            GrammarBotAnalyser.CHARACTER_LIMIT_MAX,
            GrammarBotAnalyser.CHARACTER_LIMIT_MIN,
        ))
        limit = self.config.setdefault(
            GrammarBotAnalyser.CONFIGURATION_INPUT_MAX_REQUESTS,
            GrammarBotAnalyser.INPUT_MAX_REQUESTS
        )
        if len(spans) > limit:
            # Safety measure
            raise AnalysisError(f'Too large input. Size: {len(spans)}, max: {limit}')

        offset = 0
        for span in spans:
            for item in self._analyse_api_call(span):
                item['offset'] += offset
                yield item

            offset += len(span)

    def _analyse_api_call(self, text):
        if self._remaining_requests is not None:
            overflow = self.config.setdefault(
                GrammarBotAnalyser.CONFIGURATION_REQUESTS_OVERFLOW,
                0
            )
            if self._remaining_requests + overflow <= 0:
                raise AnalysisError('Requests quota reached.')

        urltext = urllib.parse.quote(text)
        payload = f'text={urltext}&language=en-US'

        response = requests.request(
            "POST",
            GrammarBotAnalyser.URL,
            data=payload,
            headers=self._headers
        )
        data = response.json()

        if 'matches' not in data:
            if 'message' in data:
                raise AnalysisError(data['message'])
            if 'error' in data:
                raise AnalysisError(data['error'])

        self._remaining_requests = int(
            response.headers['X-RateLimit-Requests-Remaining']
        )

        for match in data['matches']:
            yield match
