from . import cpu, memory
from .hardware import printer, intc, timer, keyboard
from time import sleep

class Machine:
    def __init__(self, filename):
        self.memory = memory.Memory.load_file(filename)
        self.cpu = cpu.CPU(self.memory)

        self.intc = intc.InterruptController(self.cpu, self.memory)
        self.timer = timer.Timer(self.cpu, self.memory, self.intc)
        self.keyboard = keyboard.Keyboard(self.cpu, self.memory, self.intc)
        self.printer = printer.Printer(self.cpu, self.memory)

        self.memory.attach_hardware(self.intc)
        self.memory.attach_hardware(self.timer)
        self.memory.attach_hardware(self.keyboard)
        self.memory.attach_hardware(self.printer)

    def run(self):
        while True:
            self.cpu.decode_next_instr()
