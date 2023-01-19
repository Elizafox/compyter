#!/usr/bin/env python3

from pyarch.cpu import CPU
from collections import defaultdict
import sys

# Populate the sym table
symtable = {}
for opcode, (args, fn) in enumerate(CPU.INSTRS):
    symtable[fn.__name__] = (opcode, args)

# Label table
labeltable = {}
resolve_pending = defaultdict(list)
pc = 0
out = bytearray()

filename = sys.argv[1] if len(sys.argv) > 1 else "assemble.txt"
with open(filename, "r") as in_f:
    for line in in_f.readlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        elif line.startswith("."):
            # Got a label
            label = line[1:]
            labeltable[label] = pc
            if label in resolve_pending:
                # Resolve outstanding labels
                for addr in resolve_pending[label]:
                    data = pc.to_bytes(4, 'big')
                    out[addr:addr+4] = data

                del resolve_pending[label]

            continue

        # Filter out blanks
        statement = [x for x in filter(lambda y: y, line.split())]
        if len(statement) > 4:
            print("Invalid statement: '{}'", line)
            quit()

        # Locate the item in the symtable
        opcode, argtypes = symtable[statement[0]]
        statement = statement[1:]

        data = [opcode, 0, 0, 0]
        for i, argtype in enumerate(argtypes):
            if argtype == CPU.IA_NONE:
                continue

            if i > len(statement):
                print("Invalid statement: '{}'", line)
                quit()

            offset = (i + 1) * 4
            arg = statement[i]
            if arg.startswith("."):
                label = arg[1:]
                if label in labeltable:
                    # Excellent, symbol resolved
                    arg = labeltable[label]
                else:
                    # Ope, not yet
                    resolve_pending[label].append(pc + offset)
                    arg = 0
            else:
                arg = int(arg, base=16)

            data[i + 1] = arg

        # Write out the data
        for i in data:
            out += i.to_bytes(4, 'big')

        # Increment program counter to next instr
        pc += 16

with open("image", "wb") as out_f:
    out_f.write(out)
