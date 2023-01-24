from . import intc
from ..util import set_word_byte, get_word_byte
from time import sleep
from threading import Thread

class Timer(intc.InterruptHardware):
    INT_NUM = 32

    ADDR_BEGIN = 0xffffefc9
    ADDR_END = 0xffffefcc

    def __init__(self, cpu, memory, intc):
        super().__init__(cpu, memory, intc)

        self.duration = 0

        self.timer_thread = Thread(target=self.timer, daemon=True)
        self.timer_thread.start()

        self.cpu.register_thread(self.timer_thread)

    def timer(self):
        while not self.cpu.exit_event.is_set():
            sleep(self.duration / 1000)
            if self.duration > 0:
                self.interrupt()

    def __getitem__(self, item):
        return get_word_byte(self.duration, item)

    def __setitem__(self, item, val):
        self.duration = set_word_byte(self.duration, item, val)
