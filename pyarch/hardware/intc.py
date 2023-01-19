from . import Hardware
from ..util import set_word_byte, get_word_byte, in_range

from threading import Thread, Event, Lock
from queue import Queue

class InterruptHardware(Hardware):
    INT_NUM = -1

    def __init__(self, cpu, memory, intc):
        super().__init__(cpu, memory)
        self.intc = intc

    def interrupt(self):
        self.intc.interrupt(self.INT_NUM)


class InterruptController(Hardware):
    ADDR_BEGIN = 0xffffffce
    ADDR_END = 0xfffffffe

    INTC_MASK = 0x0        # 0xffffffce
    INTC_REG_INTNUM = 0x4  # 0xffffffd2
    INTC_REG_INTVEC = 0x8  # 0xffffffd6
    INTC_ADD_INT = 0xc     # 0xffffffda
    INTC_DEL_INT = 0x10    # 0xffffffde
    INTC_GET_INT = 0x14    # 0xffffffe2
    INTC_JMP_INSTR = 0x18  # 0xffffffe6

    def __init__(self, cpu, memory):
        super().__init__(cpu, memory)

        # Registers
        self.reg_intnum = 0
        self.reg_intvec = 0

        # Internal interrupt state
        self.interrupts = {}
        self.current = 0
        self.pending = Queue()
        self.unmasked = Event()
        self.interrupt_lock = Lock()

        self.pp_task = Thread(target=self.process_pending, daemon=True)
        self.pp_task.start()

        self.cpu.register_thread(self.pp_task)

    def process_pending(self):
        while not self.cpu.exit_event.is_set():
            interrupt = self.pending.get()

            self.unmasked.wait()
            if not self.unmasked.is_set():
                # Spurious wakeup
                continue

            # Mask all further interrupts to avoid races
            # Callee must unmask interrupts manually
            self.unmasked.clear()

            self.interrupt_nowait(interrupt)

    def interrupt(self, int_num):
        self.pending.put(int_num)

    def interrupt_nowait(self, int_num):
        with self.interrupt_lock:
            if int_num not in self.interrupts:
                # Not interested, ignore it
                return

            self.current = self.interrupts[int_num]
            # If our interrupt handler is registered, then we're golden.
            self.cpu.intr()

    def __getitem__(self, item):
        with self.interrupt_lock:
            if item == self.INTC_MASK + 3:
                return int(not self.unmasked.is_set())
            elif in_range(item, self.INTC_REG_INTNUM, self.INTC_REG_INTNUM + 3):
                return get_word_byte(self.reg_intnum, item - self.INTC_REG_INTNUM)
            elif in_range(item, self.INTC_REG_INTVEC, self.INTC_REG_INTVEC + 3):
                return get_word_byte(self.reg_intvec, item - self.INTC_REG_INTVEC)
            elif item == self.INTC_JMP_INSTR + 3:
                # jmp opcode
                return 0x11
            elif in_range(item, self.INTC_JMP_INSTR + 4, self.INTC_JMP_INSTR + 7):
                # address for jmp
                return get_word_byte(self.current, item - (self.INTC_JMP_INSTR + 4))
            else:
                return 0

    def __setitem__(self, item, val):
        with self.interrupt_lock:
            if in_range(item, self.INTC_MASK, self.INTC_MASK + 3):
                self.unmasked.set() if not val else self.unmasked.clear()
            elif in_range(item, self.INTC_REG_INTNUM, self.INTC_REG_INTNUM + 3):
                self.reg_intnum = set_word_byte(self.reg_intnum, item - self.INTC_REG_INTNUM, val)
            elif in_range(item, self.INTC_REG_INTVEC, self.INTC_REG_INTVEC + 3):
                self.reg_intvec = set_word_byte(self.reg_intvec, item - self.INTC_REG_INTVEC, val)
            elif in_range(item, self.INTC_ADD_INT, self.INTC_ADD_INT + 3):
                if val > 0:
                    self.interrupts[self.reg_intnum] = self.reg_intvec
            elif in_range(item, self.INTC_DEL_INT, self.INTC_DEL_INT + 3):
                if val > 0:
                    self.interrupts.pop(self.reg_intnum, None)
            elif in_range(item, self.INTC_GET_INT, self.INTC_GET_INT + 3):
                if val > 0:
                    # No such interrupt! This is an unlikely vector address, so this is a decent sentinel.
                    self.reg_intvec = self.interrupts.get(self.reg_intnum, 0xffffffff)
            else:
                return
