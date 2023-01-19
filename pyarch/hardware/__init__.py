class Hardware:
    ADDR_BEGIN = -1
    ADDR_END = -1

    def __init__(self, cpu, memory):
        self.cpu = cpu
        self.memory = memory

    def __getitem__(self, item):
        raise NotImplementedError()

    def __setitem__(self, item):
        raise NotImplementedError()
