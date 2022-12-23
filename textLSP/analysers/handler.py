import logging


logger = logging.getLogger(__name__)


class AnalyserHandler():

    def __init__(self, settings=None):
        self.settings = dict()
        self.update_settings(settings)

    def update_settings(self, settings):
        if settings is None:
            return
