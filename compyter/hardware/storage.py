from . import Hardware
from ..util import in_range, set_word_byte, get_word_byte
import mmap
import os


class Storage(Hardware):
    ADDR_BEGIN = 0xfffffcb0
    ADDR_END = 0xfffffebf

    REG_OFFSET = 0x0
    REG_WRENABLE = 0x4
    REG_SIZE = 0x8
    REG_STORAGE = 0x10

    def __init__(self, cpu, memory, filename="storage.img"):
        super().__init__(cpu, memory)

        self.offset = 0
        self.wrenable = True
        self.storage_fd = os.open(filename, os.O_RDWR)
        self.storage_map = mmap.mmap(self.storage_fd, 0)
        self.storage_size = os.stat(self.storage_fd).st_size

    def __del__(self):
        if hasattr(self, "storage_map"):
            self.storage_map.close()

        if hasattr(self, "storage_fd"):
            self.storage_fd.close()

    def __getitem__(self, item):
        if in_range(item, self.REG_OFFSET, self.REG_OFFSET + 3):
            return get_word_byte(self.offset, item)
        elif in_range(item, self.REG_WRENABLE, self.REG_WRENABLE + 3):
            return get_word_byte(int(self.wrenable), item - self.REG_WRENABLE)
        elif in_range(item, self.REG_SIZE, self.REG_SIZE + 3):
            return get_word_byte(self.storage_size, item - self.REG_SIZE)
        elif in_range(item, self.REG_STORAGE, self.REG_STORAGE + 511):
            return self.storage_map[self.offset + (item - self.REG_STORAGE)]
        else:
            return 0

    def __setitem__(self, item, val):
        if in_range(item, self.REG_OFFSET, self.REG_OFFSET + 3):
            self.offset = set_word_byte(self.offset, item, val)
        elif in_range(item, self.REG_WRENABLE, self.REG_WRENABLE + 3):
            self.wrenable = bool(val)
        elif in_range(item, self.REG_STORAGE, self.REG_STORAGE + 511):
            if not self.wrenable:
                return
            self.storage_map[self.offset + (item - self.REG_STORAGE)] = (val & 0xff)
