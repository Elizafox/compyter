ComPyter
------
This is a very basic virtual machine in Python, complete with hardware and a hacked-together assembler.

See the examples directory for working code examples that can be used with the assembler.

Architecture description
========================
This is a basic 32-bit RISC ISA. The ISA's name is ELISA (Elly's Lighwtweight ISA). Execution begins at 0x0. It is a two's complement architecture (like most modern architectures).

### Registers
There are 32 32-bit registers. The first five registers are reserved:

1) **Register 0**: Program counter (**REG_PC**)
2) **Register 1**: Stack pointer (**REG_SP**)
3) **Register 2**: Result register (**REG_RES**)
4) **Register 3**: Carry register (**REG_CARRY**)
5) **Register 4**: Return address from interrupts (**REG_RET**)
6) **Register 5**: Trap flag (whether or not we're in an interrupt handler) (**REG_TRAP**)

## Arithmetic
`add`, `sub`, `mul`, `div`, `mod`, `shl`, `shr`, `and`, `or`, `xor`, and `not` are supported, using registers as operands and storing the result in a third register.

Immediate versions of these operations are available with an `i` suffix (except for `not`), which take a register and an immediate value.

## Load/store
There are two base instructions: `load*` and `save*`. They perform various load/store functions as the names imply.

`loadw` loads a span from the given address to the address plus 3 into a register (the order is `loadw [reg] [addr]`). `savew` likewise saves a register into an address span (the order is the same).

`loadb` loads a single byte from an address into a register (the order is the same). `savew` likewise saves a byte into an address.

`loadwr` and `savewr` work the same as `loadw` and `savew`, except the address is taken from a register instead of a fixed value. `loadbr` and `savebr` do the same, but with single bytes.

`loadwi` loads an immediate value into a register (the order is `loadwi [reg] [val]`). `savewi` saves an immediate value to an address (the order is the same). `loadbi` and `savebi` work the same, except for bytes.

`savewri` and `savebri` work like a cross between `save*r` and `save*i`. They take immediates, but will save to the address pointed to by the given register.

### Other instructions
`swap` swaps the value of two registers.

`copy` copies the value of a register into another.

## Branching
`jmp`, `jmpeq`, `jmpne`, `jmpgt`, `jmpge`, `jmplt`, `jmple` are all available, comparing two registers (except for `jmp` which is unconditional). Comparisons with immediates are available,suffixed with `i` (`jmpeqi`, `jmpnei`, `jmpgti`, `jmpgei`, `jmplti`, and `jmplei`). Jumping to memory locations pointed to by registers is supported with `r` and `ri` suffixed instructions (`jmpr`, `jmpeqr`, `jmpner`, `jmpgtr`, `jmpger`, `jmpltr`, `jmpler`, `jmpeqri`, `jmpneri`, `jmpgtri`, `jmpgeri`, `jmpltri`, `jmpleri`).

## Halting
The `halt` instruction halts the CPU, shutting down the virtual machine, and displaying the contents of all registers to the console.

### Traps/interrupts
There is one interrupt, but an interrupt controller is provided as a peripherial. The interrupt can be masked with the `dsi` instruction and unmasked with `eni`. The current mask state can be retrieved with `gti`.

To avoid races, all traps (including an interrupt) will disable interrupts. The `ret` statement will return back to the address in `REG_RET` and re-enable interrupts in a race-free way.

All traps are at fixed vectors starting at 0xfffffeff; it is recommended to use a jmp instruction at the vector to point to your actual handler:

1) **TRAP_INTR**: Interrupt vector: 0xffffff00
2) **TRAP_ILL**: Illegal instruction vector: 0xffffff10
3) **TRAP_DIV**: Division by zero vector: 0xffffff20
4) **TRAP_DTRAP**: Double trap/fault vector: 0xffffff30

#### Waiting on interrupts
It is possible to wait for an interrupt with the `wait` instruction, which will halt the CPU until an interrupt arrives and then jump to the handler.

## Hardware
There are a variety of peripherials available, with more planned.

### Printer
The world's worst printer. When enabled, it prints whatever is written to `0xfffffeff` as ASCII to the console. It also stores the last character written at that address.

### Timer
A very basic timer connected to the interrupt controller (more on that later). It uses interrupt 0x20 on the controller. A duration in milliseconds can be written to `0xfffffec9` - `0xfffffecc` as a word. When each duration passes, an interrupt will fire. Setting the duration to 0 will disable the timer.

### RTC
A very basic RTC.

The memory layout is as follows:
* `0xffffe937` - `0xffffe93a`: Year
* `0xffffe93b`: Month
* `0xffffe93c`: Day
* `0xffffe93d`: Hour
* `0xffffe93e`: Minute
* `0xffffe93f`: Second
* `0xffffe940` - `0xffffe943`: Microsecond
* `0xffffe944`: Latch; when a non-zero value is written to this, the current time is latched into the registers.

### Keyboard
A very basic keyboard controller. It uses interrupt 0x40 on the controller. Writing anything but zero to `0xffffefc1` - `0xffffefc4` enables it. It is disabled by writing 0 to the same address.

Keystrokes can be retrieved by reading from `0xffffefc5` - `0xffffefc8` when an interrupt fires.

### Storage
A very basic storage controller. It features a 512-byte window for reading/writing, an offset register for moving the window, a read/write enable register, and a read-only size register.

The emulated storage device is backed by a file. It should be a multiple of 512 bytes in size.

The offset register is at `0xffffedb0` - `0xffffedb3` and is absolute (i.e. to change to the next window, you must add 512 to the register). The read/write register (0 for enable, 1 for disable) is at `0xffffedb4` - `0xffffedb7`. The size register is at `0xffffedb8` - `0xffffedbb`. The window is at `0xffffedc0` - `0xffffefbf`.

### Internet
A basic Internet controller wrapping the Berkeley sockets API. This is done for convenience as an entire IP stack would be painful to write.

The registers are as follows:

* `0xffffe94f` - `0xffffe95e`: Address register. Can store an IPv4 or IPv6 address.
* `0xffffe95f` - `0xffffe962`: IP version register. Store `0x1` here for IPv4, or `0x2` for IPv6.
* `0xffffe963` - `0xffffe966`: Protocol to use. Store `0x1` here for TCP, or `0x2` for UDP.
* `0xffffe967` - `0xffffe96a`: Current handle. This is used to specify what socket is being used, or the socket returned from the socket command.
* `0xffffe96b` - `0xffffe96e`: Command register. This is used to send commands to the controller.
* `0xffffe96f` - `0xffffe972`: Parameters register. This is used to store or fetch parameters for commands.
* `0xffffe973` - `0xffffe976`: Status register. This can be checked to see if a command succeeded or failed.
* `0xffffe977` - `0xffffe97a`: Asynchronous operation register. This is used when an interrupt is fired to determine what operation should be performed on the given handle. More on this later.
* `0xffffe97b` - `0xffffe97e`: Asynchronous handle register. This is used when an interrupt is fired to determine what handle needs to be serviced.
* `0xffffe9ab` - `0xffffe9ae`: Buffer size register. Used to set the current buffer size. Can never be greater than 1024.

In addition, there is a buffer:
* `0xffffe9af` - `0xffffedaf`: Buffer area.

#### Commands
By writing a value to the command register, an operation is performed. Note that although the entire command register is checked, the command is only executed when a byte is written to `0xfffff86e` (the last byte of the register).

Upon failure, the status register is set to a negative value, and the buffer will contain a detailed string about the error.

##### NOP (`0x00`)
No-op.

##### SOCKET (`0x01`)
Create a socket using the parameters in the IP version and protocol registers.

The socket will be stored in the current handle register, which can be used to refer to the socket for all other operations.

##### BIND (`0x02`)
Bind the socket in the current handle register to the address in the address register and the port in the parameter register.

##### CONNECT (`0x03`)
Connect the socket in the current handle register to the address in the address register and the port in the parameter register.

##### LISTEN (`0x04`)
Set the socket in the current handle register to listen. The parameter register may be set to set the listen backlog.

##### ACCEPT (`0x05`)
Accept a connection from the socket in the current handle register. The address register will contain the address of the client, and the parameter register will contain the port on the other end. The current handle register will be updated with the client's socket.

##### CLOSE (`0x06`)
Close the socket in the current handle register. This command always succeeds.

##### SETSOCKOPT (`0x07`)
This is not yet implemented.

##### GETSOCKOPT (`0x08`)
This is not yet implemented.

##### RECV (`0x09`)
Receive data on the socket in the current handle register. If the parameter register is non-zero, out-of-band data will be received. The received data will be stored in the buffer, and the buffer size register updated to reflect the amount of data received.

Note that a zero-length read means the socket has been closed by the remote peer.

##### SEND (`0x0a`)
Send data on the socket in the current handle register. The data is sourced from the buffer. Only the amount of bytes in the buffer length register will be transferred. If the parameter register is non-zero, out-of-band data will be sent.

The actual number of bytes transferred will be stored in the parameter register.

##### RECVMSG (`0x0b`)
Receive data on the socket in the current handle register, but in a connectionless way (i.e. UDP). If the parameter register is non-zero, out-of-band data will be received. The received data will be stored in the buffer, and the buffer size register updated to reflect the amount of data received. The client address will be stored in the address register, and the client port will be stored in the parameter register.

##### SENDMSG (`0x0c`)
Send data on the socket in the current handle register, but in a connectionless way (i.e. UDP). The destination address is stored in the address register, and the destination port is stored in the parameter register. The data is sourced from the buffer. Only the amount of bytes in the buffer length register will be transferred. If the **status** register is non-zero, out-of-band data will be received.

##### GETADDRINFO (`0x0d`)
Resolve the ASCII hostname stored in the buffer of the length specified in the buffer length register into IP addresses. The IP addresses will be stored sequentially in the following format (the numbers are bytes):

```
 0     2     4     6     8     10    12    14    16    18    20
+------------+------------------------------------------------+
| IP type    | Address                                        |
+------------+------------------------------------------------+
```

IP type will be `0x1` for IPv4, and `0x2` for IPv6.

Note that in the unlikely event there are more than 51 entries, they will be silently dropped (as the buffer will be exhausted).

##### GETNAMEINFO (`0x0e`)
Resolve the IP stored in the address register to a hostname. The hostname will be stored in the buffer and the buffer length set to the length of the hostname. Although hostnames greater than 255 characters are a violation of RFC1035, they will be truncated if returned to the buffer size. This should not be a practical problem.

##### ASYNC\_START (`0x0f`)
Register the socket in the current handle register for interrupt notification (asynchronous behaviour).

The parameter register will be read as a bitmask, with `0x1` denoting interest in notifications that a socket is ready for reading and `0x2` denoting interest in notifications that a socket is ready for writing.

When the socket is ready for reading and/or writing, the interrupt controller will be signalled with interrupt `0xc0`. The async operation register will contain a mask of events the socket is ready for, and the socket will be stored in the async handle register. The reason for these separate registers is to avoid clobbering any existing writes to the Internet controller's registers, which would result in unfortunate bugs when the interrupt handler ends.

After an asynchronous operation is complete, an `ASYNC_DONE` command must be issued to unblock the controller and prepare for the next event (if any).

##### ASYNC\_STOP (`0x10`)
Unregister the socket in the current handle register from interrupt notification. This must be done before the socket is closed.

##### ASYNC\_DONE (`0x10`)
After an asynchronous operation is complete, this command must be issued to unblock the controller and prepare for the next event (if any).

### Interrupt controller
This is by far the second most complex peripherial, after the Internet controller.

Writing anything but zero to `0xfffffece` - `0xfffffed1` will enable the interrupt controller. Writing zero will disable it.

There are two registers: the interrupt number and interrupt vector.

The interrupt number is stored at `0xfffffed2` - `0xfffffed5`. The address vector is stored at `0xfffffed6` - `0xfffffed0`.

#### Adding a vector
Writing anything to `0xffffefda` - `0xffffefdd` will add the vector stored in the interrupt number and vector to the interrupt table. When an interrupt fires, it will jump to that vector, provided the interrupt handler for the CPU is set to the handler for the interrupt controller.

#### Removing a vector
Writing anything non-zero to `0xffffefde` - `0xffffefe1` will delete the vector for interrupt number. The interrupt vector register is ignored. If the interrupt doesn't exist, this is a no-op.

#### Retrieving a vector
Writing anything non-zero to `0xffffefe2` - `0xffffefe5` will store the current vector for the interrupt number in the register. The interrupt vector register's contents are replaced. If no such interrupt exists, `0xffffffff` will be written instead.

#### Triggering an interrupt
Writing anything non-zero to `0xffffefe6` - `0xffffefe9` will trigger the interrupt in the interrupt number register. The interrupt vector register is ignored.

#### Installing the handler
To use this interrupt controller, the handler `jmp FFFFEFEA` must be installed for the interrupt trap. This will redirect the request to the interrupt controller, which will `jmp` to the handler. If no handler is installed, it will `jmp` to 0 (effectively a reset). This behaviour may change.
