from . import Hardware
import sys


class Printer(Hardware):
    ADDR_BEGIN = 0xffffefff
    ADDR_END = 0xffffefff

    def __init__(self, cpu, memory):
        super().__init__(cpu, memory)
        self.char = 0

    def __getitem__(self, item):
        return self.char

    def __setitem__(self, item, val):
        self.char = val
        sys.stdout.write(chr(val))
        sys.stdout.flush()
