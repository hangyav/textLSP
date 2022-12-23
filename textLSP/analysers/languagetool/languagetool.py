import logging

from ..analyser import Analyser


logger = logging.getLogger(__name__)


class LanguageToolAnalyser(Analyser):
    def __init__(self, config):
        self.config = config
        logger.warning('Languagetool loaded')
