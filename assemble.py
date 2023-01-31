#!/usr/bin/env python3
from assembler.grammar import program
from struct import pack
from collections import defaultdict
from sys import argv


symtable_label = {}
label_pending = defaultdict(list)
output = []


def do_parse(p):
    for stmt in p:
        if "special_stmt" in stmt:
            if stmt[0] == "align":
                align = stmt[1] - (len(output) % stmt[1])
                output.extend(0 for x in range(align))
            elif stmt[0] == "zero":
                output.extend(0 for x in range(stmt[1]))
            elif stmt[0] == "data":
                for data in stmt[1:]:
                    if isinstance(data, int):
                        output.extend(pack(">I", data))
                    elif isinstance(data, float):
                        output.extend(pack(">f", data))
                    elif isinstance(data, str):
                        output.extend(data.encode("utf-8"))
                    else:
                        raise Exception("Don't know how to unpack " + repr(type(data)))
        elif "label_stmt" in stmt:
            if stmt[0] in symtable_label:
                raise Exception("Duplicate label found: " + stmt[0])

            symtable_label[stmt[0]] = len(output)

            # Resolve pending symbols
            for i in label_pending.pop(stmt[0], []):
                output[i:i+4] = pack(">I", symtable_label[stmt[0]])
        elif "inst_stmt" in stmt:
            output.extend(pack(">I", stmt[0]))
            params = stmt[1:]
            for param in params:
                if isinstance(param, int):
                    output.extend(pack(">I", param))
                elif isinstance(param, str):
                    if param in symtable_label:
                        output.extend(pack(">I", symtable_label[param]))
                    else:
                        # Dummy it out for now, add to list of pending symbols
                        label_pending[param].append(len(output))
                        output.extend(pack(">I", 0))

            output.extend(0 for x in range(4 * (3 - len(params))))


if __name__ == "__main__":
    if len(argv) < 3:
        if len(argv) < 2:
            filename_in = "test.txt"
        else:
            filename_in = argv[1]
    else:
        filename_in = argv[1]
        filename_out = argv[2]

    p = program.parse_file(filename_in, parse_all=True)

    do_parse(p)
    if len(label_pending) > 0:
        raise Exception("Unresolved labels: " + repr(label_pending))


with open("image", "wb") as f:
    f.write(bytearray(output))
