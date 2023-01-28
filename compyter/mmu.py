import enum
from functools import lru_cache


class PTEAccess(enum.IntFlag):
    PTE_EXECUTE = 0x1
    PTE_WRITE = 0x2
    PTE_READ = 0x4


class PageFaultException(Exception):
    def __init__(self, addr):
        self.addr = addr
        super().__init__(addr)


class InvalidBasePointerException(Exception):
    pass


class PTE:
    __slots__ = ("addr", "rwx", "dirty", "acc", "usable", "user", "phys", "present", "resvd")

    def __init__(self, addr, rwx, dirty, acc, usable, user, phys, present, resvd):
        assert addr <= 0xfffff, "addr is {}".format(hex(addr))
        self.addr = addr
        self.rwx = rwx
        self.dirty = dirty
        self.acc = acc
        self.usable = usable
        self.user = user
        self.phys = phys
        self.present = present
        self.resvd = resvd

    def __repr__(self):
        return f"PTE(addr={self.addr}, " \
               f"rwx={bin(self.rwx)}, " \
               f"dirty={self.dirty}, " \
               f"acc={self.acc}, " \
               f"usable={self.usable}, " \
               f"user={self.user}, " \
               f"phys={self.phys}, " \
               f"present={self.present}, " \
               f"resvd={self.resvd})"

    @property
    def read(self):
        return bool(self.rwx & PTEAccess.PTE_READ)

    @read.setter
    def read(self, val):
        if val:
            self.rwx |= PTEAccess.PTE_READ
        else:
            self.rwx &= ~PTEAccess.PTE_READ

    @property
    def write(self):
        return bool(self.rwx & PTEAccess.PTE_WRITE)

    @write.setter
    def write(self, val):
        if val:
            self.rwx |= PTEAccess.PTE_WRITE
        else:
            self.rwx &= ~PTEAccess.PTE_WRITE

    @property
    def execute(self):
        return bool(self.rwx & PTEAccess.PTE_EXECUTE)

    @execute.setter
    def execute(self, val):
        if val:
            self.rwx |= PTEAccess.PTE_EXECUTE
        else:
            self.rwx &= ~PTEAccess.PTE_EXECUTE

    @classmethod
    def from_bytes(cls, pte):
        if len(pte) > 4:
            pte = pte[0:4]

        # First byte: high byte of PFN
        b = pte[0]
        addr = b << 12

        # Second byte: low byte of PFN
        b = pte[1]
        addr |= b << 4

        # Third byte: first four bits of PFN, rwx bits, dirty bit
        b = pte[2]
        addr |= (b & 0xf0) >> 4
        rwx = (b & 0xe) >> 1
        dirty = b & 0x1

        # Fourth byte: acc bit, usable bit, user bit, nextptr enable bit
        b = pte[3]
        acc = (b & 0x80) >> 7
        usable = (b & 0x40) >> 6
        user = (b & 0x20) >> 5
        phys = (b & 0x10) >> 4
        present = (b & 0x8) >> 3
        resvd = b & 0x7

        return cls(addr, rwx, dirty, acc, usable, user, phys, present, resvd)

    def to_bytes(self):
        pte = bytearray(4)

        # Address
        pte[0] = (self.addr & 0xff000) >> 12  # High byte
        pte[1] = (self.addr & 0x00ff0) >> 4   # Low byte
        pte[2] = (self.addr & 0x0000f) << 4   # Last four bits

        pte[2] |= (self.rwx & 0x7) << 1

        pte[2] |= (self.dirty & 0x1)

        pte[3] = (self.acc & 0x1) << 7
        pte[3] |= (self.usable & 0x1) << 6
        pte[3] |= (self.user & 0x1) << 5
        pte[3] |= (self.phys & 0x1) << 4
        pte[3] |= (self.present & 0x1) << 3

        return pte


class MMU:
    def __init__(self, memory, cpu):
        self.baseptr = 0
        self.memory = memory
        self.cpu = cpu
        self.vaddr = 0

    @lru_cache
    def get_pte(self, addr):
        if self.baseptr + 4096 > 0xffffffff:
            raise InvalidBasePointerException(self.baseptr)

        page = addr >> 12
        page_lvl1 = (page & 0xffc00) >> 10
        page_lvl2 = page & 0x003ff

        # Check level 1
        pte_offset = self.baseptr + (page_lvl1 << 2)
        pte_lvl1 = PTE.from_bytes(self.memory[pte_offset:pte_offset+4])
        if pte_lvl1.phys:
            # This is a large page
            return (0x400000, pte_lvl1)

        # Get the next level of page table
        pte_offset = (pte_lvl1.addr << 12) + (page_lvl2 << 2)
        pte_lvl2 = PTE.from_bytes(self.memory[pte_offset:pte_offset+4])

        # Regular size page
        return (0x1000, pte_lvl2)

    def pte_writeback(self, addr, pte):
        if self.baseptr + 4096 > 0xffffffff:
            raise InvalidBasePointerException(self.baseptr)

        page = addr >> 12
        page_lvl1 = (page & 0xffc00) >> 10
        page_lvl2 = page & 0x003ff

        # Check level 1
        pte_offset = self.baseptr + (page_lvl1 << 2)
        if not pte.phys:
            # Get the next level of page table
            pte_offset = (pte_lvl1.addr << 12) + (page_lvl2 << 2)

        self.memory[pte_offset:pte_offset+4] = pte.to_bytes()

    @lru_cache
    def get_page(self, addr, mask):
        if not self.cpu.registers.mmu_bit:
            # Direct translation
            addr &= 0xfffff000
            return self.memory[addr:addr+0x1000]

        pagesize, pte = self.get_pte(addr)
        if pte.rwx & mask == 0:
            # Nope
            self.vaddr = addr
            raise PageFaultException(addr)

        pte.acc = 1
        self.pte_writeback(addr, pte)

        page = pte.addr << 12
        return self.memory[page:page+pagesize]

    @lru_cache
    def get_address(self, addr, mask=PTEAccess.PTE_READ):
        mask |= PTEAccess.PTE_READ

        if self.cpu.registers.mmu_bit:
            pagesize, pte = self.get_pte(addr)
            if not (pte & mask):
                # Mask doesn't match
                raise PageFaultException(addr)

            if not pte.user and self.cpu.registers.user_bit:
                # Kernel mode only, sorry
                raise PageFaultException(addr)
        
            pte.acc = 1
            self.pte_writeback(addr, pte)

        return self.memory[addr]

    def write_page(self, addr, data):
        if not self.cpu.registers.mmu_bit:
            addr &= 0xfffff000
            self.memory[addr:addr+0x1000] = data
            return

        pagesize, pte = self.get_pte(addr)
        if not pte.write:
            self.vaddr = addr
            raise PageFaultException(addr)
        
        pte.dirty = 1
        self.pte_writeback(addr, pte)

        page = pte.addr << 12
        self.memory[page:page+pagesize] = data
        
    def write_address(self, addr, value, mask=PTEAccess.PTE_WRITE):
        mask |= PTEAccess.PTE_WRITE

        if self.cpu.registers.mmu_bit:
            pagesize, pte = self.get_pte(addr)
            if not (pte & mask):
                raise PageFaultException(addr)

            if not pte.user and self.cpu.registers.user_bit:
                # Kernel mode only, sorry
                raise PageFaultException(addr)

            pte.dirty = 1
            self.pte_writeback(addr, pte)

        self.memory[addr] = value

    def clear_cache(self):
        self.get_page.cache_clear()
        self.get_address.cache_clear()
        self.get_pte.cache_clear()
