import logging

from collections import defaultdict
from language_tool_python import LanguageTool
from pygls.workspace import Workspace

from ..analyser import Analyser
from ...workspace import BaseDocument


logger = logging.getLogger(__name__)


LANGUAGE_MAP = defaultdict(lambda: 'en-US')
LANGUAGE_MAP['en'] = 'en-US'
LANGUAGE_MAP['en-US'] = 'en-US'


class LanguageToolAnalyser(Analyser):
    def __init__(self, config):
        self.config = dict()
        self.update_settings(config)
        self.tools = dict()

    def update_settings(self, settings):
        # TODO
        self.config = settings

    def did_open(self, document: BaseDocument):
        raise NotImplementedError()

    def did_change(self, document: BaseDocument):
        raise NotImplementedError()

    def did_close(self, workspace: Workspace, document: BaseDocument):
        doc_langs = {
            document.language
            for _, document in workspace.documents.items()
        }
        tool_langs = set(self.tools.keys())

        for lang in tool_langs - doc_langs:
            self.tools[lang].close()
            del self.tools[lang]

    def close(self):
        for lang, tool in self.tools.items():
            tool.close()

    def _get_mapped_language(self, language):
        return LANGUAGE_MAP[language]

    def _get_tool_for_language(self, language):
        lang = self._get_mapped_language(language)
        if lang in self.tools:
            return self.tools[lang]

        tool = LanguageTool(lang)
        self.tools[lang] = tool

        return tool
