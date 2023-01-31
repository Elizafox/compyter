import pyparsing as pp
from functools import partial


reg_map = {
    # GP regs
    "0" : 0x0,
    "1" : 0x1,
    "2" : 0x2,
    "3" : 0x3,
    "4" : 0x4,
    "5" : 0x5,
    "6" : 0x6,
    "7" : 0x7,
    "8" : 0x8,
    "9" : 0x9,
    "10" : 0xa,
    "11" : 0xb,
    "12" : 0xc,
    "13" : 0xd,
    "14" : 0xe,
    "15" : 0xf,
    "16" : 0x10,
    "17" : 0x11,
    "18" : 0x12,
    "19" : 0x13,
    "20" : 0x14,
    "21" : 0x15,
    "22" : 0x16,
    "23" : 0x17,
    "24" : 0x18,
    "25" : 0x19,
    "26" : 0x1a,
    "27" : 0x1b,
    "28" : 0x1c,
    "29" : 0x1d,
    "30" : 0x1e,
    "31" : 0x1f,
    # special regs
    "pc" : 0x20,
    "sp" : 0x21,
    "result" : 0x22,
    "res" : 0x22,
    "carry" : 0x23,
    "c" : 0x23,
    "ret" : 0x24,
    "return" : 0x24,
    "status" : 0x25,
    "stat" : 0x25,
    "vaddr" : 0x26,
    "va" : 0x26,
    "baseptr" : 0x27,
    "bp": 0x27
}


pp.ParserElement.set_default_whitespace_chars(" \t")

# Integer literals
dec_int_literal = pp.common.signed_integer().set_name("dec_int_literal")
hex_int_literal = pp.Combine(pp.Literal("0x").suppress() + pp.Word(pp.hexnums)).set_name("hex_int_literal")
bin_int_literal = pp.Combine(pp.Literal("0b").suppress() + pp.Word("01")).set_name("bin_int_literal")

dec_int_literal.add_parse_action(lambda t: int(t[0]) & 0xffffffff)
hex_int_literal.add_parse_action(lambda t: int(t[0], base=16) & 0xffffffff)
bin_int_literal.add_parse_action(lambda t: int(t[0], base=2) & 0xffffffff)

int_literal = (dec_int_literal ^ hex_int_literal ^ bin_int_literal)

# Reals
float_literal = pp.common.sci_real().set_name("float_literal")
float_literal.add_parse_action(lambda t: float(t[0]))

# Registers
reg_names = pp.Or([pp.Literal(k) for k in reg_map.keys()])

# Statement literals
reg_literal = pp.Combine(pp.Literal("$").suppress() + reg_names)
addr_literal = pp.Combine(pp.Literal("&").suppress() + pp.Word(pp.hexnums))
num_literal = (int_literal ^ float_literal)
string_literal = pp.QuotedString("\"").set_name("string_literal")

reg_literal.add_parse_action(lambda t: reg_map[t[0]])
addr_literal.add_parse_action(lambda t: int(t[0], base=16))

# Labels
label_name = pp.Word(pp.alphanums + "_")
label = pp.Combine(pp.Literal(".").suppress() + label_name)
label_stmt = label("label_stmt")

# Specials/pseudo ops
special_char = pp.Literal("!").suppress()
special_ops = [
    (pp.Keyword("data"), pp.OneOrMore(num_literal ^ string_literal)),
    (pp.Keyword("align"), int_literal),
    (pp.Keyword("zero"), int_literal)
]
special_stmt = pp.Or([pp.Combine(special_char + x[0]) + x[1] for x in special_ops])("special_stmt")

# Instructions
inst_op_reg = reg_literal
inst_op_addr = addr_literal ^ label
inst_op_immed = num_literal ^ label

inst_op_reg_addr = (inst_op_reg + inst_op_addr)
inst_op_reg_reg = (inst_op_reg + inst_op_reg)
inst_op_reg_immed = (inst_op_reg + inst_op_immed)
inst_op_reg_reg_reg = (inst_op_reg + inst_op_reg + inst_op_reg)
inst_op_reg_reg_addr = (inst_op_reg + inst_op_reg + inst_op_addr)
inst_op_reg_immed_reg = (inst_op_reg + inst_op_immed + inst_op_reg)
inst_op_reg_immed_addr = (inst_op_reg + inst_op_immed + inst_op_addr)
inst_op_immed_reg = (inst_op_immed + inst_op_reg)
inst_op_immed_addr = (inst_op_immed + inst_op_addr)

inst_ops = [
    ("nop", None),
    ("savew", inst_op_reg_addr),
    ("loadw", inst_op_reg_addr),
    ("saveb", inst_op_reg_addr),
    ("loadb", inst_op_reg_addr),
    ("savewr", inst_op_reg_reg),
    ("loadwr", inst_op_reg_reg),
    ("savebr", inst_op_reg_reg),
    ("loadbr", inst_op_reg_reg),
    ("savewi", inst_op_immed_addr),
    ("loadwi", inst_op_reg_immed),
    ("savebi", inst_op_immed_addr),
    ("loadbi", inst_op_reg_immed),
    ("savewri", inst_op_immed_reg),
    ("savebri", inst_op_immed_reg),
    ("add", inst_op_reg_reg_reg),
    ("sub", inst_op_reg_reg_reg),
    ("mul", inst_op_reg_reg_reg),
    ("div", inst_op_reg_reg_reg),
    ("mod", inst_op_reg_reg_reg),
    ("addi", inst_op_reg_immed_reg),
    ("subi", inst_op_reg_immed_reg),
    ("muli", inst_op_reg_immed_reg),
    ("divi", inst_op_reg_immed_reg),
    ("modi", inst_op_reg_immed_reg),
    ("jmp", inst_op_addr),
    ("jmpr", inst_op_reg),
    ("jmplt", inst_op_reg_reg_addr),
    ("jmpgt", inst_op_reg_reg_addr),
    ("jmple", inst_op_reg_reg_addr),
    ("jmpge", inst_op_reg_reg_addr),
    ("jmpeq", inst_op_reg_reg_addr),
    ("jmpne", inst_op_reg_reg_addr),
    ("jmplti", inst_op_reg_immed_addr),
    ("jmpgti", inst_op_reg_immed_addr),
    ("jmplei", inst_op_reg_immed_addr),
    ("jmpgei", inst_op_reg_immed_addr),
    ("jmpeqi", inst_op_reg_immed_addr),
    ("jmpnei", inst_op_reg_immed_addr),
    ("jmpltr", inst_op_reg_reg_reg),
    ("jmpgtr", inst_op_reg_reg_reg),
    ("jmpler", inst_op_reg_reg_reg),
    ("jmpger", inst_op_reg_reg_reg),
    ("jmpeqr", inst_op_reg_reg_reg),
    ("jmpner", inst_op_reg_reg_reg),
    ("jmpltri", inst_op_reg_reg_reg),
    ("jmpgtri", inst_op_reg_reg_reg),
    ("jmpleri", inst_op_reg_reg_reg),
    ("jmpgeri", inst_op_reg_reg_reg),
    ("jmpeqri", inst_op_reg_reg_reg),
    ("jmpneri", inst_op_reg_reg_reg),
    ("halt", None),
    ("intr", None),
    ("rfe", None),
    ("wait", None),
    ("swap", inst_op_reg_reg),
    ("copy", inst_op_reg_reg),
    ("and", inst_op_reg_reg_reg),
    ("or", inst_op_reg_reg_reg),
    ("xor", inst_op_reg_reg_reg),
    ("andi", inst_op_reg_immed_reg),
    ("ori", inst_op_reg_immed_reg),
    ("xori", inst_op_reg_immed_reg),
    ("not", inst_op_reg_reg),
    ("shl", inst_op_reg_reg_reg),
    ("shr", inst_op_reg_reg_reg),
    ("shli", inst_op_reg_immed_reg),
    ("shri", inst_op_reg_immed_reg),
    ("cpuid", None),
    ("strapr", inst_op_reg_addr),
    ("strapi", inst_op_immed_addr)
]
    
def keyword_parse_action(i, tok):
    tok[0] = i


# Build the ops list
inst_ops_parse = []
for i, (inst_name, inst_op) in enumerate(inst_ops):
    inst = pp.Keyword(inst_name).add_parse_action(partial(keyword_parse_action, i))
    if inst_op:
        inst += inst_op

    inst_ops_parse.append(inst)

inst_stmt = pp.Or(inst_ops_parse)("inst_stmt")

# Comments
comment = (pp.Literal("#") ^ pp.Literal("//")) + pp.rest_of_line()
comment = comment.set_name("comment")

# Statements
eol = pp.line_end().suppress()
stmt = pp.Optional(pp.Group(label_stmt ^ special_stmt ^ inst_stmt)) + eol
stmt.ignore(comment)

program = (pp.string_start() + pp.ZeroOrMore(stmt) + pp.string_end())
