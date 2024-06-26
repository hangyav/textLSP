import logging

from typing import Optional, List
from lsprotocol.types import (
        CompletionParams,
        CompletionItem,
        CompletionList,
        CodeActionParams,
        CodeAction,
)
from pygls.server import LanguageServer
from lsprotocol.types import MessageType
from transformers import pipeline

from ..analyser import Analyser
from ...types import ConfigurationError
from ... import nn_utils


logger = logging.getLogger(__name__)


class HFCompletionAnalyser(Analyser):
    CONFIGURATION_GPU = 'gpu'
    CONFIGURATION_MODEL = 'model'
    CONFIGURATION_TOP_K = 'topk'
    CONFIGURATION_CONTEXT_SIZE = 'context_size'
    CONFIGURATION_QUANTIZE = 'quantize'

    SETTINGS_DEFAULT_GPU = False
    SETTINGS_DEFAULT_MODEL = 'bert-base-multilingual-cased'
    SETTINGS_DEFAULT_TOP_K = 5
    SETTINGS_DEFAULT_CONTEXT_SIZE = 50
    SETTINGS_DEFAULT_QUANTIZE = 32

    def __init__(self, language_server: LanguageServer, config: dict, name: str):
        super().__init__(language_server, config, name)
        use_gpu = self.config.get(self.CONFIGURATION_GPU, self.SETTINGS_DEFAULT_GPU)
        device = nn_utils.get_device(use_gpu)

        quanitze = self.config.setdefault(self.CONFIGURATION_QUANTIZE, self.SETTINGS_DEFAULT_QUANTIZE)
        model_kwargs = dict()
        try:
            nn_utils.set_quantization_args(quanitze, device, model_kwargs)
        except ConfigurationError as e:
            language_server.show_message(
                f'{self.name}: {str(e)}',
                MessageType.Error,
            )
            self.config[self.CONFIGURATION_QUANTIZE] = 32

        model = self.config.get(self.CONFIGURATION_MODEL, self.SETTINGS_DEFAULT_MODEL)
        self.completor = pipeline(
            'fill-mask',
            model,
            device=device,
            model_kwargs=model_kwargs,
        )
        if self.completor.tokenizer.mask_token is None:
            raise ConfigurationError(f'The tokenizer of {model} does not have a MASK token.')

    def should_run_on(self, event: str) -> bool:
        return False

    def get_code_actions(self, params: CodeActionParams) -> Optional[List[CodeAction]]:
        return None

    def get_completions(self, params: Optional[CompletionParams] = None) -> Optional[CompletionList]:
        doc = self.get_document(params)
        doc_len = len(doc.cleaned_source)
        offset = doc.offset_at_position(params.position, True)
        offset = max(0, min(offset, doc_len-1))
        in_paragraph_offset = self.config.get(self.CONFIGURATION_CONTEXT_SIZE, self.SETTINGS_DEFAULT_CONTEXT_SIZE)
        start = max(0, offset-in_paragraph_offset)
        length = min(doc_len-offset+in_paragraph_offset, 2*in_paragraph_offset)
        in_paragraph_offset = offset-start-1  # we need the character before the position
        if in_paragraph_offset >= length:
            return None

        paragraph = doc.cleaned_source[start:start+length]
        # we look for whitespace in the uncleaned source since some positions
        # in the file might not be mapped to the cleaned_source which leads to
        # unexpected behaviour
        uncleaned_offset = max(0, doc.offset_at_position(params.position)-1)
        # XXX: this still gets activated in e.g. commented lines
        if doc.source[uncleaned_offset] in {' ', '\n'}:
            return self._get_text_completions(paragraph, in_paragraph_offset)

    def _get_text_completions(self, paragraph, in_paragraph_offset):
        input = ''
        if in_paragraph_offset > 0:
            input += paragraph[:in_paragraph_offset+1].strip(' ')
            if input[-1] != '\n':
                input += ' '
        input += f'{self.completor.tokenizer.mask_token} '
        if in_paragraph_offset < len(paragraph) - 1:
            input += paragraph[in_paragraph_offset+1:].strip()

        res = list()
        for item in self.completor(
            input,
            top_k=self.config.get(self.CONFIGURATION_TOP_K, self.SETTINGS_DEFAULT_TOP_K),
        ):
            completion_item = CompletionItem(
                label=item['token_str'],
            )
            res.append(completion_item)
        return res
