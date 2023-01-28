import enum
import dataclasses


class RegisterName(enum.IntEnum):
    # GP regs
    REG_0 = 0x0
    REG_1 = 0x1
    REG_2 = 0x2
    REG_3 = 0x3
    REG_4 = 0x4
    REG_5 = 0x5
    REG_6 = 0x6
    REG_7 = 0x7
    REG_8 = 0x8
    REG_9 = 0x9
    REG_10 = 0xa
    REG_11 = 0xb
    REG_12 = 0xc
    REG_13 = 0xd
    REG_14 = 0xe
    REG_15 = 0xf
    REG_16 = 0x10
    REG_17 = 0x11
    REG_18 = 0x12
    REG_19 = 0x13
    REG_20 = 0x14
    REG_21 = 0x15
    REG_22 = 0x16
    REG_23 = 0x17
    REG_24 = 0x18
    REG_25 = 0x19
    REG_26 = 0x1a
    REG_27 = 0x1b
    REG_28 = 0x1c
    REG_29 = 0x1d
    REG_30 = 0x1e
    REG_31 = 0x1f

    # Special registers
    REG_PC = 0x20       # Program counter
    REG_SP = 0x21       # Stack pointer
    REG_RES = 0x22      # Result
    REG_CARRY = 0x23    # Carry
    REG_RET = 0x24      # Return vector
    REG_STATUS = 0x25   # Status (privileged)
    REG_VADDR = 0x26    # Virutal address (privileged)
    REG_BPTR = 0x27     # Base pointer (privileged)

    # Reserved for emulator usage
    REG_RSVD = 0x28    # Reserved for internal use
    REG_LAST = 0x29


class StatusBit(enum.IntFlag):
    MMU_ENABLE =  0x80000000
    USER_OLD = 0x00000020
    INTR_OLD = 0x00000010
    USER_PREV = 0x00000008
    INTR_PREV = 0x00000004
    USER = 0x00000002
    INTR = 0x00000001


class PrivilegeException(Exception):
    pass


class RegisterFile:
    # Privileged registers
    PRIV_REGS = (RegisterName.REG_STATUS,
                 RegisterName.REG_VADDR,
                 RegisterName.REG_BPTR)
    
    def __init__(self, cpu):
        self.registers = [0] * (RegisterName.REG_LAST)
        self.cpu = cpu

    @property
    def mmu_bit(self):
        return self.registers[RegisterName.REG_STATUS] & StatusBit.MMU_ENABLE

    @mmu_bit.setter
    def mmu_bit(self, val):
        # Force the MMU bit
        if val:
            self.registers[RegisterName.REG_STATUS] |= StatusBit.MMU_ENABLE
        else:
            self.registers[RegisterName.REG_STATUS] &= ~StatusBit.MMU_ENABLE
    
    @property
    def user_old_bit(self):
        return self.registers[RegisterName.REG_STATUS] & StatusBit.USER_OLD

    @user_old_bit.setter
    def user_old_bit(self, val):
        # Force set the user bit
        if val:
            self.registers[RegisterName.REG_STATUS] |= StatusBit.USER_OLD
        else:
            self.registers[RegisterName.REG_STATUS] &= ~StatusBit.USER_OLD

    @property
    def intr_old_bit(self):
        return self.registers[RegisterName.REG_STATUS] & StatusBit.INTR_OLD

    @intr_old_bit.setter
    def intr_old_bit(self, val):
        # Force set the intr bit
        if val:
            self.registers[RegisterName.REG_STATUS] |= StatusBit.INTR_OLD
        else:
            self.registers[RegisterName.REG_STATUS] &= ~StatusBit.INTR_OLD

    @property
    def user_prev_bit(self):
        return self.registers[RegisterName.REG_STATUS] & StatusBit.USER_PREV

    @user_prev_bit.setter
    def user_prev_bit(self, val):
        # Force set the user bit
        if val:
            self.registers[RegisterName.REG_STATUS] |= StatusBit.USER_PREV
        else:
            self.registers[RegisterName.REG_STATUS] &= ~StatusBit.USER_PREV

    @property
    def intr_prev_bit(self):
        return self.registers[RegisterName.REG_STATUS] & StatusBit.INTR_PREV

    @intr_prev_bit.setter
    def intr_prev_bit(self, val):
        # Force set the intr bit
        if val:
            self.registers[RegisterName.REG_STATUS] |= StatusBit.INTR_PREV
        else:
            self.registers[RegisterName.REG_STATUS] &= ~StatusBit.INTR_PREV

    @property
    def user_bit(self):
        return self.registers[RegisterName.REG_STATUS] & StatusBit.USER

    @user_bit.setter
    def user_bit(self, val):
        # Force set the user bit
        if val:
            self.registers[RegisterName.REG_STATUS] |= StatusBit.USER
        else:
            self.registers[RegisterName.REG_STATUS] &= ~StatusBit.USER

    @property
    def intr_bit(self):
        return self.registers[RegisterName.REG_STATUS] & StatusBit.INTR

    @intr_bit.setter
    def intr_bit(self, val):
        # Force set the intr bit
        if val:
            self.registers[RegisterName.REG_STATUS] |= StatusBit.INTR
        else:
            self.registers[RegisterName.REG_STATUS] &= ~StatusBit.INTR

    @property
    def vaddr(self, val):
        return self.registers[RegisterName.REG_VADDR]

    @vaddr.setter
    def vaddr(self, val):
        # Force set the vaddr register
        self.registers[RegisterName.REG_VADDR] = val

    @property
    def bptr(self):
        return self.registers[RegisterName.REG_BPTR]

    @bptr.setter
    def bptr(self, val):
        # Force set the base pointer
        self.registers[RegisterName.REG_BPTR] = val

    @property
    def rsvd(self):
        return self.registers[RegisterName.REG_RSVD]

    @rsvd.setter
    def rsvd(self, val):
        self.registers[RegisterName.REG_RSVD] = val

    def __getitem__(self, item):
        if item in self.PRIV_REGS and self.user_bit:
            raise PrivilegeException()

        return self.registers[item]

    def __setitem__(self, item, val):
        if item in self.PRIV_REGS and self.user_bit:
            raise PrivilegeException()

        self.registers[item] = val

        # XXX - this is messy
        cur_intr = self.intr_bit
        if cur_intr and self.cpu.intr_pending:
            # Fire interrupt if enabled.
            self.cpu.intr()

    def pretty_format(self):
        ret = []
        for i, x in enumerate(self.registers[0:-1]):
            reg_name = RegisterName(i).name
            ret.append(f"{reg_name:10} = 0x{x:08x}")

        return ",\n".join(ret)
