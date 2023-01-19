from . import Hardware
import sys


class Printer(Hardware):
    ADDR_BEGIN = 0xffffffff
    ADDR_END = 0xffffffff

    def __init__(self, cpu, memory):
        super().__init__(cpu, memory)
        self.char = 0

    def __getitem__(self, item):
        return self.char

    def __setitem__(self, item, value):
        self.char = value
        sys.stdout.write(chr(value))
        sys.stdout.flush()
