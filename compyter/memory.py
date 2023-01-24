class Memory:
    def __init__(self, memory=None):
        self.hardware_mmio = {}

        self.trap_vectors = bytearray(4096)

        if memory is None:
            self.memory = [0] * 255
        else:
            self.memory = memory

    @classmethod
    def load_file(cls, filename):
        with open(filename, 'rb') as f:
            memory = list(f.read())

        return cls(memory)

    def attach_hardware(self, hardware):
        for i in range(hardware.ADDR_BEGIN, hardware.ADDR_END + 1):
            self.hardware_mmio[i] = hardware

    def __len__(self):
        # XXX - physical memory size only!
        return len(self.memory)

    def __getitem__(self, item):
        if item >= 0xfffff000:
            # Trap vector, redirect
            return self.trap_vectors[item - 0xfffff000]

        if item in self.hardware_mmio:
            hardware = self.hardware_mmio[item]
            return hardware[item - hardware.ADDR_BEGIN]

        return self.memory[item]

    def __setitem__(self, item, value):
        if item >= 0xfffff000:
            # Trap vector, redirect
            self.trap_vectors[item - 0xfffff000] = value & 0xff
            return

        if item in self.hardware_mmio:
            hardware = self.hardware_mmio[item]
            hardware[item - hardware.ADDR_BEGIN] = value
            return

        self.memory[item] = value & 0xff
