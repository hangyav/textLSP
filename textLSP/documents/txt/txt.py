import re

from lsprotocol.types import Position, Range

from ..document import CleanableDocument
from ...types import Interval


class TxtDocument(CleanableDocument):
    CONFIGURATION_PARSE = 'parse'

    DEFAULT_PARSE = True

    PATTERN_BREAK_INLINE = re.compile('([^\n])\n([^\n])')

    def _clean_source(self):
        parse = self.config.setdefault(
            self.CONFIGURATION_PARSE,
            self.DEFAULT_PARSE,
        )
        if parse:
            self._cleaned_source = self.PATTERN_BREAK_INLINE.sub(r'\1 \2', self.source)
        else:
            self._cleaned_source = self.source

    def position_at_offset(self, offset: int, cleaned=False) -> Position:
        return super().position_at_offset(offset, False)

    def range_at_offset(self, offset: int, length: int, cleaned=False) -> Range:
        return super().range_at_offset(offset, length, False)

    def offset_at_position(self, position: Position, cleaned=False) -> int:
        return super().offset_at_position(position, False)

    def paragraphs_at_range(self, position_range: Range, cleaned=False) -> Interval:
        return super().paragraphs_at_range(position_range, False)

    def last_position(self, cleaned=False):
        return super().last_position(False)
