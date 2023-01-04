import logging
import requests
import urllib.parse

from lsprotocol.types import (
        DidOpenTextDocumentParams,
        Diagnostic,
)
from pygls.server import LanguageServer

from ..analyser import Analyser, AnalysisError
from ...utils import ConfigurationError, batch_text, TEXT_PASSAGE_PATTERN


logger = logging.getLogger(__name__)


class GrammarBotAnalyser(Analyser):
    CONFIGURATION_API_KEY = 'api_key'
    CONFIGURATION_INPUT_MAX_REQUESTS = 'input_max_requests'
    CONFIGURATION_REQUESTS_OVERFLOW = 'requests_overflow'

    URL = "https://grammarbot.p.rapidapi.com/check"
    CHARACTER_LIMIT_MAX = 8000
    CHARACTER_LIMIT_MIN = 7500
    INPUT_MAX_REQUESTS = 10

    def __init__(self, language_server: LanguageServer, config: dict):
        super().__init__(language_server, config)
        # TODO save this somewhere
        self._remaining_requests = None
        if GrammarBotAnalyser.CONFIGURATION_API_KEY not in self.config:
            raise ConfigurationError('Reqired parameter: grammarbot.api_key')
        self._headers = {
            'content-type': 'application/x-www-form-urlencoded',
            'X-RapidAPI-Key': self.config[GrammarBotAnalyser.CONFIGURATION_API_KEY],
            'X-RapidAPI-Host': 'grammarbot.p.rapidapi.com'
        }

    def did_open(self, params: DidOpenTextDocumentParams):
        doc = self.get_document(params)
        self.init_diagnostics(doc)
        diagnostics = list()
        source = doc.cleaned_source

        for match in self._analyse(source):
            token = source[match['offset']:match['offset']+match['length']]
            replacements = ''
            if len(match['replacements']) > 0:
                replacements = ', '.join(item['value'] for item in match['replacements'])
                replacements = f' -> {replacements}'
            diagnostics.append(
                Diagnostic(
                    range=doc.range_at_offset(match['offset'], match['length'], True),
                    message=f'"{token}"{replacements}: {match["message"]}',
                    source='grammarbot',
                    severity=self.get_severity(),
                    code=f'grammarbot:{match["rule"]["id"]}',
                )
            )

        self.add_diagnostics(doc, diagnostics)

    def _analyse(self, text):
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
            for item in self._analyse_section(span):
                item['offset'] += offset
                yield item

            offset += len(span)

    def _analyse_section(self, text):
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
        self._remaining_requests = int(
            response.headers['X-RateLimit-Requests-Remaining']
        )
        data = response.json()

        if 'matches' not in data:
            if 'message' in data:
                raise AnalysisError(data['message'])
            if 'error' in data:
                raise AnalysisError(data['error'])

        for match in data['matches']:
            yield match
