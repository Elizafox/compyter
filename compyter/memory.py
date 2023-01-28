class Memory:
    def __init__(self, memory=None):
        self.hardware_mmio = {}

        self.trap_vectors = bytearray(4096)

        if memory is None:
            self.memory = bytearray(4096)
        else:
            self.memory = memory

    @classmethod
    def load_file(cls, filename):
        with open(filename, 'rb') as f:
            memory = bytearray(f.read())

        if len(memory) < 4096:
            memory.extend(0 for _ in range(4096 - len(memory)))

        return cls(memory)

    def attach_hardware(self, hardware):
        for i in range(hardware.ADDR_BEGIN, hardware.ADDR_END + 1):
            self.hardware_mmio[i] = hardware

    def __len__(self):
        # XXX - physical memory size only!
        return len(self.memory)

    def __getitem__(self, item):
        if isinstance(item, slice):
            m = max(item.start, item.stop)
            return bytearray(self[i] for i in range(*item.indices(m + 1)))

        if item >= 0xfffff000:
            # Trap vector, redirect
            return self.trap_vectors[item - 0xfffff000]

        if item in self.hardware_mmio:
            hardware = self.hardware_mmio[item]
            return hardware[item - hardware.ADDR_BEGIN]

        return self.memory[item]

    def __setitem__(self, item, value):
        if isinstance(item, slice):
            m = max(item.start, item.stop)
            for i, j in enumerate(range(*item.indices(m + 1))):
                self[j] = value[i]

            return

        if item >= 0xfffff000:
            # Trap vector, redirect
            self.trap_vectors[item - 0xfffff000] = value & 0xff
            return

        if item in self.hardware_mmio:
            hardware = self.hardware_mmio[item]
            hardware[item - hardware.ADDR_BEGIN] = value
            return

        self.memory[item] = value & 0xff
