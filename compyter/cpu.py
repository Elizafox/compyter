from threading import RLock, Event
from time import sleep

class CPU:
    CPU_VERSION = 0x1

    MAXVAL = (2 ** 32) - 1

    # Special regs
    REG_PC = 0x0
    REG_SP = 0x1
    REG_RES = 0x2
    REG_CARRY = 0x3
    REG_RET = 0x4
    REG_TRAP = 0x5
    REG_RESVD = 0x20  # Reserved for internal use

    # Traps
    TRAP_INTR = 0x10  # Only one interrupt, but we use an interrupt controller
    TRAP_ILL = 0x20
    TRAP_DIV = 0x30
    TRAP_DTRAP = 0x40

    def __init__(self, memory):
        self.memory = memory
        self.registers = [0] * (self.REG_RESVD + 1)
        self.cpu_lock = RLock()
        self.threads = []
        self.exit_event = Event()
        self.intr_event = Event()
        self.intr_mask = False
        self.intr_pending = False

    def register_thread(self, thread):
        self.threads.append(thread)

    def end_threads(self):
        self.exit_event.set()
        for thread in self.threads:
            thread.join(timeout=1)

    def trap(self, addr):
        self.intr_event.set()

        with self.cpu_lock:
            self.dsi()

            if self.registers[self.REG_TRAP] and addr != self.TRAP_DTRAP:
                # We've already trapped and the flag wasn't cleared!
                return self.trap(self.TRAP_DTRAP)

            self.registers[self.REG_TRAP] = 1
            self.registers[self.REG_RET] = self.registers[self.REG_PC]
            self.jmp(addr)

            self.intr_event.clear()

    @staticmethod
    def _binary_to_signed(num):
        # Convert a binary number to a signed representation
        if num > 0x7fffffff:
            # Negative
            num -= 0x100000000

        return num

    def jmp(self, addr):
        if addr < 0:
            print("Illegal address", addr)
            self.trap(self.TRAP_ILL)
            return

        self.registers[self.REG_PC] = addr

    def jmpr(self, reg1):
        self.jmp(self.registers[reg1])

    def jmpeq(self, reg1, reg2, addr):
        if self.registers[reg1] == self.registers[reg2]:
            self.jmp(addr)

    def jmpeqi(self, reg1, val, addr):
        self.registers[self.REG_RESVD] = val
        self.jmpeq(reg1, self.REG_RESVD, addr)

    def jmpeqr(self, reg1, reg2, reg3):
        self.jmpeq(reg1, reg2, self.registers[reg3])

    def jmpeqri(self, reg1, val, reg2):
        self.jmpeqi(reg1, val, self.registers[reg2])

    def jmpne(self, reg1, reg2, addr):
        if self.registers[reg1] != self.registers[reg2]:
            self.jmp(addr)

    def jmpnei(self, reg1, val, addr):
        self.registers[self.REG_RESVD] = val
        self.jmpne(reg1, self.REG_RESVD, addr)

    def jmpner(self, reg1, reg2, reg3):
        self.jmpne(reg1, reg2, self.registers[reg3])

    def jmpneri(self, reg1, val, reg2):
        self.jmpnei(reg1, val, self.registers[reg2])

    def jmpgt(self, reg1, reg2, addr):
        op1 = self._binary_to_signed(self.registers[reg1])
        op2 = self._binary_to_signed(self.registers[reg2])
        if op1 > op2:
            self.jmp(addr)

    def jmpgti(self, reg1, val, addr):
        self.registers[self.REG_RESVD] = val
        self.jmpgt(reg1, self.REG_RESVD, addr)

    def jmpgtr(self, reg1, reg2, reg3):
        self.jmpgt(reg1, reg2, self.registers[reg3])

    def jmpgtri(self, reg1, val, reg2):
        self.jmpgti(reg1, val, self.registers[reg2])

    def jmpge(self, reg1, reg2, addr):
        op1 = self._binary_to_signed(self.registers[reg1])
        op2 = self._binary_to_signed(self.registers[reg2])
        if op1 >= op2:
            self.jmp(addr)

    def jmpgei(self, reg1, val, addr):
        self.registers[self.REG_RESVD] = val
        self.jmpge(reg1, self.REG_RESVD, addr)

    def jmpger(self, reg1, reg2, reg3):
        self.jmpge(reg1, reg2, self.registers[reg3])

    def jmpgeri(self, reg1, val, reg2):
        self.jmpgei(reg1, val, self.registers[reg2])

    def jmplt(self, reg1, reg2, addr):
        op1 = self._binary_to_signed(self.registers[reg1])
        op2 = self._binary_to_signed(self.registers[reg2])
        if op1 < op2:
            self.jmp(addr)

    def jmplti(self, reg1, val, addr):
        self.registers[self.REG_RESVD] = val
        self.jmplt(reg1, self.REG_RESVD, addr)

    def jmpltr(self, reg1, reg2, reg3):
        self.jmplt(reg1, reg2, self.registers[reg3])

    def jmpltri(self, reg1, val, reg2):
        self.jmplti(reg1, val, self.registers[reg2])

    def jmple(self, reg1, reg2, addr):
        op1 = self._binary_to_signed(self.registers[reg1])
        op2 = self._binary_to_signed(self.registers[reg2])
        if op1 <= op2:
            self.jmp(addr)

    def jmplei(self, reg1, val, addr):
        self.registers[self.REG_RESVD] = val
        self.jmple(reg1, self.REG_RESVD, addr)

    def jmpler(self, reg1, reg2, reg3):
        self.jmple(reg1, reg2, self.registers[reg3])

    def jmpleri(self, reg1, val, reg2):
        self.jmplei(reg1, val, self.registers[reg2])

    def add(self, reg1, reg2, reg3):
        result = self.registers[reg1] + self.registers[reg2]
        self.registers[reg3] = result & 0xffffffff
        self.registers[self.REG_CARRY] = int(result > self.MAXVAL)

    def addi(self, reg1, val, reg2):
        self.registers[self.REG_RESVD] = val
        return self.add(reg1, self.REG_RESVD, reg2)

    def sub(self, reg1, reg2, reg3):
        result = self.registers[reg1] - self.registers[reg2]
        self.registers[reg3] = result & 0xffffffff
        self.registers[self.REG_CARRY] = 0

    def subi(self, reg1, val, reg2):
        self.registers[self.REG_RESVD] = val
        return self.sub(reg1, self.REG_RESVD, reg2)

    def mul(self, reg1, reg2, reg3):
        result = self.registers[reg1] * self.registers[reg2]
        self.registers[reg3] = result & 0xffffffff
        self.registers[self.REG_CARRY] = int(result > self.MAXVAL)

    def muli(self, reg1, val, reg2):
        self.registers[self.REG_RESVD] = val
        return self.mul(reg1, self.REG_RESVD, reg2)

    @staticmethod
    def _divmod(dividend, divisor):
        divisor_compl = (divisor ^ 0xffffffff) + 1

        quotient = dividend
        remainder = 0

        for _ in range(0, 32):
            carry = quotient >> 31

            quotient <<= 1
            quotient &= 0xffffffff

            remainder <<= 1
            remainder &= 0xffffffff
            remainder |= carry

            test = (remainder + divisor_compl) & 0xffffffff
            if (test & 0x80000000) == 0:
                remainder = test
                quotient |= 1

        return (quotient, remainder)

    def div(self, reg1, reg2, reg3):
        if self.registers[reg2] == 0:
            # division by zero trap
            self.trap(self.TRAP_DIV)
            return

        result = self._divmod(self.registers[reg1], self.registers[reg2])
        self.registers[reg3] = result[0] & 0xffffffff
        self.registers[self.REG_CARRY] = 0

    def divi(self, reg1, val, reg2):
        self.registers[self.REG_RESVD] = val
        return self.div(reg1, self.REG_RESVD, reg2)

    def mod(self, reg1, reg2, reg3):
        if self.registers[reg2] == 0:
            # Division by zero trap
            self.trap(self.TRAP_DIV)
            return

        result = self._divmod(self.registers[reg1], self.registers[reg2])
        self.registers[reg3] = result[1] & 0xffffffff
        self.registers[self.REG_CARRY] = 0

    def modi(self, reg1, val, reg2):
        self.registers[self.REG_RESVD] = val
        return self.mod(reg1, self.REG_RESVD, reg2)

    def loadw(self, reg1, addr):
        if addr + 3 > self.MAXVAL:
            self.trap(self.TRAP_ILL)
            return

        self.registers[reg1] = (self.memory[addr] << 24)
        self.registers[reg1] |= (self.memory[addr + 1] << 16)
        self.registers[reg1] |= (self.memory[addr + 2] << 8)
        self.registers[reg1] |= self.memory[addr + 3]

    def loadwr(self, reg1, reg2):
        self.loadw(reg1, self.registers[reg2])

    def loadwi(self, reg1, val):
        self.registers[reg1] = val

    def savew(self, reg1, addr):
        if addr + 3 > self.MAXVAL:
            self.trap(self.TRAP_ILL)
            return

        self.memory[addr] = (self.registers[reg1] >> 24) & 0xff
        self.memory[addr + 1] = (self.registers[reg1] >> 16) & 0xff
        self.memory[addr + 2] = (self.registers[reg1] >> 8) & 0xff
        self.memory[addr + 3] = (self.registers[reg1]) & 0xff

    def savewr(self, reg1, reg2):
        self.savew(reg1, self.registers[reg2])

    def savewi(self, val, addr):
        self.registers[self.REG_RESVD] = val
        self.savew(self.REG_RESVD, addr)

    def savewri(self, val, reg1):
        self.savewi(val, self.registers[reg1])

    def loadb(self, reg1, addr):
        self.registers[reg1] = self.memory[addr]

    def loadbr(self, reg1, reg2):
        self.loadb(reg1, self.registers[reg2])

    def loadbi(self, reg1, val):
        self.registers[reg1] = val & 0xff

    def saveb(self, reg1, addr):
        self.memory[addr] = self.registers[reg1] & 0xff

    def savebr(self, reg1, reg2):
        self.saveb(reg1, self.registers[reg2])

    def savebi(self, val, addr):
        self.registers[self.REG_RESVD] = val
        self.saveb(self.REG_RESVD, addr)

    def savebri (self, val, reg1):
        self.savebi(val, self.registers[reg1])

    def nop(self):
        pass

    def halt(self):
        print([hex(x) for x in self.registers])
        self.end_threads()
        quit()

    def intr(self):
        if self.intr_mask:
            self.intr_pending = True
        else:
            self.intr_pending = False
            self.trap(self.TRAP_INTR)

    def ret(self):
        self.registers[self.REG_TRAP] = 0
        self.registers[self.REG_PC] = self.registers[self.REG_RET]
        self.eni()

    def eni(self):
        self.intr_mask = False
        if self.intr_pending:
            self.intr()

    def dsi(self):
        self.intr_mask = True

    def wait(self):
        self.intr_event.wait()

    def swap(self, reg1, reg2):
        temp = self.registers[reg1]
        self.registers[reg1] = reg2
        self.registers[reg2] = temp

    def copy(self, reg1, reg2):
        self.registers[reg1] = self.registers[reg2]

    def and_(self, reg1, reg2, reg3):
        self.registers[reg3] = self.registers[reg1] & self.registers[reg2]

    def andi(self, reg1, val, reg2):
        self.registers[reg2] = self.registers[reg1] & val

    def or_(self, reg1, reg2, reg3):
        self.registers[reg3] = self.registers[reg1] | self.registers[reg2]

    def ori(self, reg1, val, reg2):
        self.registers[reg2] = self.registers[reg1] | val

    def xor_(self, reg1, reg2, reg3):
        self.registers[reg3] = self.registers[reg1] ^ self.registers[reg2]

    def xori(self, reg1, val, reg2):
        self.registers[reg2] = self.registers[reg1] ^ val

    def not_(self, reg1, reg2):
        self.registers[reg2] = (~self.registers[reg1]) & 0xffffffff

    def shl(self, reg1, reg2, reg3):
        self.registers[reg3] = (self.registers[reg1] << self.registers[reg2]) & 0xffffffff

    def shli(self, reg1, val, reg2):
        self.registers[reg2] = (self.registers[reg1] << val) & 0xffffffff

    def shr(self, reg1, reg2, reg3):
        self.registers[reg3] = self.registers[reg1] >> self.registers[reg2]

    def shri(self, reg1, val, reg2):
        self.registers[reg2] = self.registers[reg1] >> val

    def cpuid(self):
        self.registers[self.REG_RES] = self.CPU_VERSION

    # Instruction parameter types
    IA_NONE = 0
    IA_IMMED = 1
    IA_ADDR = 2
    IA_REG = 3

    # This has to come after due to scoping rules
    INSTRS = [
        # arg1      arg2      arg3       instruction_fn
        ((IA_NONE,  IA_NONE,  IA_NONE),  nop),      # 0x00
        ((IA_REG,   IA_ADDR,  IA_NONE),  savew),    # 0x01
        ((IA_REG,   IA_ADDR,  IA_NONE),  loadw),    # 0x02
        ((IA_REG,   IA_ADDR,  IA_NONE),  saveb),    # 0x03
        ((IA_REG,   IA_ADDR,  IA_NONE),  loadb),    # 0x04
        ((IA_REG,   IA_REG,   IA_NONE),  savewr),   # 0x05
        ((IA_REG,   IA_REG,   IA_NONE),  loadwr),   # 0x06
        ((IA_REG,   IA_REG,   IA_NONE),  savebr),   # 0x07
        ((IA_REG,   IA_REG,   IA_NONE),  loadbr),   # 0x08
        ((IA_IMMED, IA_ADDR,  IA_NONE),  savewi),   # 0x09
        ((IA_REG,   IA_IMMED, IA_NONE),  loadwi),   # 0x0a
        ((IA_IMMED, IA_ADDR,  IA_NONE),  savebi),   # 0x0b
        ((IA_REG,   IA_IMMED, IA_NONE),  loadbi),   # 0x0c
        ((IA_IMMED, IA_REG,   IA_NONE),  savewri),  # 0x0d
        ((IA_IMMED, IA_REG,   IA_NONE),  savebri),  # 0x0e
        ((IA_REG,   IA_REG,   IA_REG),   add),      # 0x0f
        ((IA_REG,   IA_REG,   IA_REG),   sub),      # 0x10
        ((IA_REG,   IA_REG,   IA_REG),   mul),      # 0x11
        ((IA_REG,   IA_REG,   IA_REG),   div),      # 0x12
        ((IA_REG,   IA_REG,   IA_REG),   mod),      # 0x13
        ((IA_REG,   IA_IMMED, IA_REG),   addi),     # 0x14
        ((IA_REG,   IA_IMMED, IA_REG),   subi),     # 0x15
        ((IA_REG,   IA_IMMED, IA_REG),   muli),     # 0x16
        ((IA_REG,   IA_IMMED, IA_REG),   divi),     # 0x17
        ((IA_REG,   IA_IMMED, IA_REG),   modi),     # 0x18
        ((IA_ADDR,  IA_NONE,  IA_NONE),  jmp),      # 0x19
        ((IA_REG,   IA_NONE,  IA_NONE),  jmpr),     # 0x1a
        ((IA_REG,   IA_REG,   IA_ADDR),  jmpeq),    # 0x1b
        ((IA_REG,   IA_REG,   IA_ADDR),  jmpne),    # 0x1c
        ((IA_REG,   IA_REG,   IA_ADDR),  jmplt),    # 0x1d
        ((IA_REG,   IA_REG,   IA_ADDR),  jmpgt),    # 0x1e
        ((IA_REG,   IA_REG,   IA_ADDR),  jmple),    # 0x1f
        ((IA_REG,   IA_REG,   IA_ADDR),  jmpge),    # 0x20
        ((IA_REG,   IA_IMMED, IA_ADDR),  jmpeqi),   # 0x21
        ((IA_REG,   IA_IMMED, IA_ADDR),  jmpnei),   # 0x22
        ((IA_REG,   IA_IMMED, IA_ADDR),  jmplti),   # 0x23
        ((IA_REG,   IA_IMMED, IA_ADDR),  jmpgti),   # 0x24
        ((IA_REG,   IA_IMMED, IA_ADDR),  jmplei),   # 0x25
        ((IA_REG,   IA_IMMED, IA_ADDR),  jmpgei),   # 0x26
        ((IA_REG,   IA_IMMED, IA_ADDR),  jmpeqi),   # 0x27
        ((IA_REG,   IA_IMMED, IA_ADDR),  jmpnei),   # 0x28
        ((IA_REG,   IA_IMMED, IA_ADDR),  jmplti),   # 0x29
        ((IA_REG,   IA_IMMED, IA_ADDR),  jmpgti),   # 0x2a
        ((IA_REG,   IA_IMMED, IA_ADDR),  jmplei),   # 0x2b
        ((IA_REG,   IA_IMMED, IA_ADDR),  jmpgei),   # 0x2c
        ((IA_REG,   IA_REG,   IA_REG),   jmpeqr),   # 0x2d
        ((IA_REG,   IA_REG,   IA_REG),   jmpner),   # 0x2e
        ((IA_REG,   IA_REG,   IA_REG),   jmpltr),   # 0x2f
        ((IA_REG,   IA_REG,   IA_REG),   jmpgtr),   # 0x30
        ((IA_REG,   IA_REG,   IA_REG),   jmpler),   # 0x31
        ((IA_REG,   IA_REG,   IA_REG),   jmpger),   # 0x32
        ((IA_REG,   IA_REG,   IA_REG),   jmpeqr),   # 0x33
        ((IA_REG,   IA_REG,   IA_REG),   jmpner),   # 0x34
        ((IA_REG,   IA_REG,   IA_REG),   jmpltr),   # 0x35
        ((IA_REG,   IA_REG,   IA_REG),   jmpgtr),   # 0x36
        ((IA_REG,   IA_REG,   IA_REG),   jmpler),   # 0x37
        ((IA_REG,   IA_REG,   IA_REG),   jmpger),   # 0x38
        ((IA_REG,   IA_REG,   IA_REG),   jmpeqri),  # 0x39
        ((IA_REG,   IA_REG,   IA_REG),   jmpneri),  # 0x3a
        ((IA_REG,   IA_REG,   IA_REG),   jmpltr),   # 0x3b
        ((IA_REG,   IA_REG,   IA_REG),   jmpgtri),  # 0x3c
        ((IA_REG,   IA_REG,   IA_REG),   jmpleri),  # 0x3d
        ((IA_REG,   IA_REG,   IA_REG),   jmpgeri),  # 0x3e
        ((IA_REG,   IA_REG,   IA_REG),   jmpeqri),  # 0x3f
        ((IA_REG,   IA_REG,   IA_REG),   jmpneri),  # 0x40
        ((IA_REG,   IA_REG,   IA_REG),   jmpltri),  # 0x41
        ((IA_REG,   IA_REG,   IA_REG),   jmpgtri),  # 0x42
        ((IA_REG,   IA_REG,   IA_REG),   jmpleri),  # 0x43
        ((IA_REG,   IA_REG,   IA_REG),   jmpgeri),  # 0x44
        ((IA_NONE,  IA_NONE,  IA_NONE),  halt),     # 0x45
        ((IA_NONE,  IA_NONE,  IA_NONE),  intr),     # 0x46
        ((IA_NONE,  IA_NONE,  IA_NONE),  ret),      # 0x47
        ((IA_NONE,  IA_NONE,  IA_NONE),  eni),      # 0x48
        ((IA_NONE,  IA_NONE,  IA_NONE),  dsi),      # 0x49
        ((IA_NONE,  IA_NONE,  IA_NONE),  wait),     # 0x4a
        ((IA_REG,   IA_REG,   IA_NONE),  swap),     # 0x4b
        ((IA_REG,   IA_REG,   IA_NONE),  copy),     # 0x4c
        ((IA_REG,   IA_REG,   IA_REG),   and_),     # 0x4d
        ((IA_REG,   IA_REG,   IA_REG),   or_),      # 0x4e
        ((IA_REG,   IA_REG,   IA_REG),   xor_),     # 0x4f
        ((IA_REG,   IA_IMMED, IA_REG),   andi),     # 0x50
        ((IA_REG,   IA_IMMED, IA_REG),   ori),      # 0x51
        ((IA_REG,   IA_IMMED, IA_REG),   xori),     # 0x52
        ((IA_REG,   IA_REG,   IA_NONE),  not_),     # 0x53
        ((IA_REG,   IA_REG,   IA_REG),   shl),      # 0x54
        ((IA_REG,   IA_REG,   IA_REG),   shr),      # 0x55
        ((IA_REG,   IA_IMMED, IA_REG),   shli),     # 0x56
        ((IA_REG,   IA_IMMED, IA_REG),   shri),     # 0x57
        ((IA_NONE,  IA_NONE,  IA_NONE),  cpuid),    # 0x58
    ]

    def decode_next_instr(self):
        sleep(0)
        with self.cpu_lock:
            # Each instruction is four words
            self.loadw(self.REG_RESVD, self.registers[self.REG_PC])
            opcode = self.registers[self.REG_RESVD]
            self.registers[self.REG_PC] += 4

            self.loadw(self.REG_RESVD, self.registers[self.REG_PC])
            op1 = self.registers[self.REG_RESVD]
            self.registers[self.REG_PC] += 4

            self.loadw(self.REG_RESVD, self.registers[self.REG_PC])
            op2 = self.registers[self.REG_RESVD]
            self.registers[self.REG_PC] += 4

            self.loadw(self.REG_RESVD, self.registers[self.REG_PC])
            op3 = self.registers[self.REG_RESVD]
            self.registers[self.REG_PC] += 4

            if opcode >= len(self.INSTRS):
                # Invalid opcode
                print("Error: Invalid opcode", hex(opcode))
                self.trap(self.TRAP_ILL)
                return

            # This type checks the arguments and adds the argument to the arg list
            # This makes the instruction specification more flexible
            arglist = []
            instr_type, instr_fn = self.INSTRS[opcode]
            #print(hex(self.registers[self.REG_PC] - 16), instr_fn.__name__, hex(op1), hex(op2), hex(op3))
            for (argtype, arg) in zip(instr_type, (op1, op2, op3)):
                # Type check the argument
                if argtype == self.IA_NONE:
                    continue
                elif argtype == self.IA_REG:
                    if arg > self.REG_RESVD:
                        print("Bad register", hex(arg))
                        return self.trap(self.TRAP_ILL)

                arglist.append(arg)

            instr_fn(self, *arglist)
