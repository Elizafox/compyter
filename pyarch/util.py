def in_range(c, a, b):
    return c >= a and c <= b

def set_word_byte(num, byte, val):
    mask_table = [
        0x00ffffff,
        0xff00ffff,
        0xffff00ff,
        0xffffff00,
    ]
    val &= 0xff
    byte = 3 - byte
    return (mask_table[byte] & num) | (val << (byte * 8))

def get_word_byte(num, byte):
    return (num >> ((3 - byte) * 8)) & 0xff

def set_double_byte(num, byte, val):
    mask_table = [
        0xffffffffffffff00,
		0xffffffffffff00ff,
		0xffffffffff00ffff,
		0xffffffff00ffffff,
		0xffffff00ffffffff,
		0xffff00ffffffffff,
		0xff00ffffffffffff,
		0x00ffffffffffffff,
    ]
    val &= 0xff
    byte = 7 - byte
    return (mask_table[byte] & num) | (val << (byte * 8))

def get_double_byte(num, byte):
    return (num >> ((7 - byte) * 8)) & 0xff
