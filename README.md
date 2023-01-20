PyArch
------
This is a very basic CPU architecture in Python, complete with hardware and a hacked-together assembler.

See the examples directory for working code examples that can be used with the assembler.

Architecture description
========================
This is a basic 32-bit RISC ISA. Execution begins at 0x0.

### Registers
There are 32 32-bit registers. The first five registers are reserved:

1) **Register 0**: Program counter (**REG_PC**)
2) **Register 1**: Stack pointer (**REG_SP**)
3) **Register 2**: Result register (**REG_RES**)
4) **Register 3**: Carry register (**REG_CARRY**)
5) **Register 4**: Return address from interrupts (**REG_RET**)
6) **Register 5**: Trap flag (whether or not we're in an interrupt handler) (**REG_TRAP**)

## Arithmetic
`add`, `sub`, `mul`, `div`, `shl`, `shr`, `and`, `or`, `xor`, and `not` are supported, using registers as operands and storing the result in a third register.

Immediate versions of these operations are available with an `i` suffix (except for `not`), which take a register and an immediate value.

## Load/store
There are two base instructions: `load*` and `save*`. They perform various load/store functions as the names imply.

`loadw` loads a span from the given address to the address plus 3 into a register (the order is `loadw [reg] [addr]`). `savew` likewise saves a register into an address span (the order is the same).

`loadb` loads a single byte from an address into a register (the order is the same). `savew` likewise saves a byte into an address.

`loadwr` and `savewr` work the same as `loadw` and `savew`, except the address is taken from a register instead of a fixed value. `loadbr` and `savebr` do the same, but with single bytes.

`loadwi` loads an immediate value into a register (the order is `loadwi [reg] [val]`). `savewi` saves an immediate value to an address (the order is the same). `loadbi` and `savebi` work the same, except for bytes.

### Other instructions
`swap` swaps the value of two registers.

`copy` copies the value of a register into another.

## Branching
`jmp`, `jmpeq`, `jmpne`, `jmpgt`, `jmpge`, `jmplt`, `jmple` are all available, comparing two registers (except for `jmp` which is unconditional). Comparisons with immediates are available,suffixed with `i`.

## Halting
The `halt` instruction halts the CPU, shutting down the virtual machine, and displaying the contents of all registers and memory to the console.

### Traps/interrupts
There is one interrupt, but an interrupt controller is provided as a peripherial. The interrupt can be masked with the `dsi` instruction and unmasked with `eni`.

To avoid races, all traps (including an interrupt) will disable interrupts. The `ret` statement will return back to the address in `REG_RET` and re-enable interrupts in a race-free way.

All traps are at fixed vectors; it is recommended to use a jmp instruction at the vector to point to your actual handler:

1) **TRAP_INTR**: Interrupt vector: 0x10
2) **TRAP_ILL**: Illegal instruction vector: 0x20
3) **TRAP_DIV**: Division by zero vector: 0x30
4) **TRAP_DTRAP**: Double trap/fault vector: 0x40

#### Waiting on interrupts
It is possible to wait for an interrupt with the `wait` instruction, which will halt the CPU until an interrupt arrives and then jump to the handler. 

### Hardware
There are a variety of peripherials available, with more planned.

#### Printer
The world's worst printer. When enabled, it prints whatever is written to `0xffffffff` as ASCII to the console. It also stores the last character written at that address.

#### Timer
A very basic timer connected to the interrupt controller (more on that later). It uses interrupt 0x20 on the controller. A duration in milliseconds can be written to `0xffffffc9` - `0xffffffcc` as a word. When each duration passes, an interrupt will fire. Setting the duration to 0 will disable the timer.

#### Keyboard
A very basic keyboard controller. It uses interrupt 0x40 on the controller. Writing anything but zero to `0xffffffc1` - `0xffffffc4` enables it. It is disabled by writing 0 to the same address.

Keystrokes can be retrieved by reading from `0xffffffc5` - `0xffffffc8` when an interrupt fires.

#### Storage
A very basic storage controller. It features a 512-byte window for reading/writing, an offset register for moving the window, a read/write enable register, and a read-only size register.

The emulated storage device is backed by a file. It should be a multiple of 512 bytes in size.

The offset register is at `0xfffffdb0` - `0xfffffdb3` and is absolute (i.e. to change to the next window, you must add 512 to the register). The read/write register (0 for enable, 1 for disable) is at `0xfffffdb4` - `0xfffffdb7`. The size register is at `0xfffffdb8` - `0xfffffdbb`. The window is at `0xfffffdc0` - `0xffffffbf`.

#### Interrupt controller
This is by far the most complex peripherial.

Writing anything but zero to `0xffffffce` - `0xffffffd1` will enable the interrupt controller. Writing zero will disable it.

There are two registers: the interrupt number and interrupt vector.

The interrupt number is stored at `0xffffffd2` - `0xffffffd5`. The address vector is stored at `0xffffffd6` - `0xffffffd0`.

##### Adding a vector
Writing anything to `0xffffffda` - `0xffffffdd` will add the vector stored in the interrupt number and vector to the interrupt table. When an interrupt fires, it will jump to that vector, provided the interrupt handler for the CPU is set to the handler for the interrupt controller.

##### Removing a vector
Writing anything non-zero to `0xffffffde` - `0xffffffe1` will delete the vector for interrupt number. The interrupt vector register is ignored. If the interrupt doesn't exist, this is a no-op.

##### Retrieving a vector
Writing anything non-zero to `0xffffffe2` - `0xffffffe5` will store the current vector for the interrupt number in the register. The interrupt vector register's contents are replaced. If no such interrupt exists, `0xffffffff` will be written instead.

##### Triggering an interrupt
Writing anything non-zero to `0xffffffe6` - `0xffffffe9` will trigger the interrupt in the interrupt number register. The interrupt vector register is ignored.

##### Installing the handler
To use this interrupt controller, the handler `jmp FFFFFFEA` must be installed for the interrupt trap. This will redirect the request to the interrupt controller, which will `jmp` to the handler. If no handler is installed, it will `jmp` to 0 (effectively a reset). This behaviour may change.
