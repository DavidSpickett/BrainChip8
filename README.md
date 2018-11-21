# BrainChip8

This is a partly functional Brainfuck interpreter for running on a Chip8. It uses generate.py to insert the program as ASCII text into the assembly file before using [RustChip8](https://github.com/DavidSpickett/RustChip8) to assemble and run it. 

## Example

Subtract two numbers, 5 and 3, to get 2.
```
+++++>+++[-<->]<.
```

Output:
```
$ make
python generate.py
rchip8 -a brain.s brain.o
rchip8 -i brain.o 20
0x0200 : 0x1404 : JP 0x404
<...>
0x0456 : 0xf065 : LD V0, [I]
----- Chip8 State -----
PC: 0x045a I: 0x0300
Delay Timer: 0 Sound Timer: 0
V00: 0x02 V01: 0x01 V02: 0x01 V03: 0x00 V04: 0x00 V05: 0x00 V06: 0x00 V07: 0x00 
V08: 0x00 V09: 0x00 V10: 0x00 V11: 0x00 V12: 0x00 V13: 0x00 V14: 0x00 V15: 0x00 
Stack:
<...>
thread 'main' panicked at 'BRK instruction encountered at PC 0x0458', system/mod.rs:216:25
```
As you can see the answer of 2 is in V0.

If you look at 'brain.s' you can see how the program was embedded:
```
program:
.word 0x2b2b
.word 0x2b2b
.word 0x2b3e
<...>
```

## Notes

Input is not supported and the output comamnd ('.') only works for a single byte and immediatley ends the program.

The '[' and ']' commands have no bounds on them when they look for the corresponding bracket. So if the program is malformed what the interpreter does is undefined. The Python script will check the length of the program and the characters it uses but doesn't check for matching brackets.

Null bytes will cause the program to stop (branch to self). One of these is placed at the end of the program regardless of whether you include one directly. (well two but that's just because I don't have a '.byte')

## Memory Layout

The Chip8 only has 1 12 bit address register I. We can load that directly with a fixed address and we can add a V register to it. This means that (putting aside repeatedley adding to I) we can only influence the bottom 8 bits at runtime. (also putting aside any kind of JIT style soloution)

To enable this the memory is laid out as follows:
```
location=0x200
  jp entry          // 2 bytes
  Brainfuck program // 252 bytes
  .word 0x0000      // program terminator, 2 bytes
location=0x300
  data cells        // 256 bytes
location=0x400
  main loop
  <...etc...>
```

This limits the program size to 252 characters, but it means that the data section is on a 256 byte boundary. Which keeps things simple when loading the data pointer. If the data section were offset and began at say 0x302, its 'last' address would be 0x300 due to the last byte wrapping. Which is some other data which we don't want to modify.

The program is always terminated with null bytes to prevent us running into this issue. (it starts at 0x202)
