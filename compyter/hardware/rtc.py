from . import Hardware
from ..util import set_word_byte, get_word_byte, in_range
from datetime import datetime


class RTC(Hardware):
    ADDR_BEGIN = 0xfffff837
    ADDR_END = 0xfffff84e

    REG_YEAR = 0x0      # 0xfffff837
    REG_MONTH = 0x4     # 0xfffff83b
    REG_DAY = 0x5       # 0xfffff83c
    REG_HOUR = 0x6      # 0xfffff83d
    REG_MIN = 0x7       # 0xfffff83e
    REG_SEC = 0x8       # 0xfffff83f
    REG_USEC = 0x9      # 0xfffff840
    REG_LATCH = 0xd     # 0xfffff844

    def __init__(self, cpu, memory):
        super().__init__(cpu, memory)

        self.now = datetime.now()

    def __getitem__(self, item):
        if in_range(item, self.REG_YEAR, self.REG_YEAR + 3):
            return get_word_byte(self.now.year, item)
        elif item == self.REG_MONTH:
            return self.now.month
        elif item == self.REG_DAY:
            return self.now.day
        elif item == self.REG_HOUR:
            return self.now.hour
        elif item == self.REG_MIN:
            return self.now.minute
        elif item == self.REG_SEC:
            return self.now.second
        elif in_range(item, self.REG_USEC, self.REG_USEC + 3):
            return get_word_byte(self.now.microsecond, item - self.REG_USEC)
        else:
            return 0

    def __setitem__(self, item, val):
        # All writes are ignored because setting time requires superuser privileges
        # And it isn't worth it to maintain an offset
        if item == self.REG_LATCH and val:
            self.now = datetime.now()
