from . import intc
from ..util import set_word_byte, get_word_byte, in_range
from threading import Thread
import tty
import sys
import termios

class Keyboard(intc.InterruptHardware):
    INT_NUM = 64

    ADDR_BEGIN = 0xffffffc1
    ADDR_END = 0xffffffc8

    INPUT_REG_ENABLE = 0x0
    INPUT_REG_CHAR = 0x4

    def __init__(self, cpu, memory, intc):
        super().__init__(cpu, memory, intc)

        self.enabled = False
        self.char = 0

        self.input_thread = Thread(target=self.input, daemon=True)
        self.input_thread.start()

        self.cpu.register_thread(self.input_thread)

    def input(self):
        # Terminal shenanigans to enable raw input
        orig_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin)
        try:
            while not self.cpu.exit_event.is_set():
                # We're in a thread so it's okay to block
                self.char = ord(sys.stdin.read(1)[0])
                if self.enabled:
                    self.interrupt()
        finally:
            # Set it back to the way it was
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, orig_settings)
            print()

    def __getitem__(self, item):
        if item == self.INPUT_REG_ENABLE + 3:
            return int(self.enabled) & 0xff
        elif in_range(item, self.INPUT_REG_CHAR, self.INPUT_REG_CHAR + 3):
            return get_word_byte(self.char, item - self.INPUT_REG_CHAR)
        else:
            return 0

    def __setitem__(self, item, val):
        if item == self.INPUT_REG_ENABLE + 3:
            self.enabled = bool(val)
        elif in_range(item, self.INPUT_REG_CHAR, self.INPUT_REG_CHAR + 3):
            self.char = set_word_byte(self.char, item - self.INPUT_REG_CHAR, val)
