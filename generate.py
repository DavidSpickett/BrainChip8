def program_to_words(prog):
  """
  Convert the text program 'prog' into
  .word instrs to insert into the interpter program.

  >>> program_to_words('')
  []
  >>> program_to_words('>')
  ['.word 0x3e00']
  >>> program_to_words('><')
  ['.word 0x3e3c']
  >>> program_to_words('>'*253)
  Traceback (most recent call last):
  ...
  RuntimeError: Programs can only be up to 252 characters long.
  >>> program_to_words('><+-k[+]')
  Traceback (most recent call last):
  ...
  RuntimeError: Invalid characters in program.

  """
  if not prog:
    return []

  # 2 for the inital jump and 2 for the null termination
  if len(prog) > (256-2-2):
    raise RuntimeError("Programs can only be up to 252 characters long.")
  
  if set(prog).difference(set('><+-.,[]')):
    raise RuntimeError('Invalid characters in program.')

  # Each .word is 16 bits
  if len(prog) % 2:
    prog += '\0'

  words = []
  for i in range(0, len(prog), 2):
    words.append('.word 0x{:04x}'.format(ord(prog[i+1]) | (ord(prog[i]) << 8)))

  return words

def pad_program(prog):
  """
  Expand generated .word sequence to cover 252 bytes
  which will put the data section on a 256 byte boundary
  and allow us to access all of that.
  """
  while len(prog) < (252/2):
    prog.append('.word 0x0000')
  return "\n".join(prog)

def generate_handler_switch():
  template = '''\
    sne v0, 0x{:02x}
    jp handle_{}'''

  commands = [
      ('>', 'greater_than'),
      ('<', 'less_than'),
      ('+', 'plus'),
      ('-', 'minus'),
      ('.', 'dot'),
      (',', 'comma'),
      ('[', 'open_square'),
      (']', 'close_square'),
      ('\0', 'end_prog'),
  ]
  handlers = []
  for command, name in commands:
    handlers.append(template.format(
      ord(command), name))

  return "\n".join(handlers)

interpreter_asm = """\
  jp entry

// This will start at 202, and end with a terminator
// so our program offset is actually a max of 256 - 4 = 252
program:
{prog}
// Terminator
.word 0x0000

// Program is padded to be 252 bytes long, which means
// that this section begins at 0x300 and we can offset
// all 256 bytes of it
data:
{data}

data_offset:
  .word 0x0000
instr_offset:
  // FF so we can always incremement, the first one wraps us to 0
  .word 0xFF00

entry:
  // Also increments pointer 
  call get_command
  // Handle command
  {handler_switch}
  brk

handle_greater_than:
  // Increment data pointer
  call get_data_offset
  add v0, 1
  call store_data_offset
  jp entry

handle_less_than:
  // Decrement data pointer
  call get_data_offset
  ld v1, 1
  sub v0, v1
  call store_data_offset
  jp entry

handle_plus:
  // Increment data byte
  call get_data_ptr
  ld v0, [I]
  add v0, 1
  ld [I], v0
  jp entry

handle_minus:
  // Decrement data byte
  call get_data_ptr
  ld v0, [I]
  ld v1, 1
  sub v0, v1
  ld [I], v0
  jp entry

handle_dot:
  // TODO: don't just end here, some fake printf?
  // Output byte at data ptr
  // Just going to load it in a reg and break for now, quickest way to see it
  call get_data_ptr
  ld v0, [I]
  brk
  jp entry

handle_comma:
  // TODO: get a byte of input from the input section
  brk
  jp entry

handle_open_square:
  // If value at data pointer is 0, skip forward to cmd after ']'
  call get_data_ptr
  ld v0, [I]

  // If it's 0 move to next command
  se v0, 0
  jp entry

  // Otherwise search forward for a ']'
  call get_instr_ptr
  // For incrementing I
  ld v1, 1
  // To count how many times we incremented it
  // (since we can't read back I)
  ld v2, 0

closing_loop:
  // Note that we always use v0, since it loads from 0 to Vn
  ld v0, [I]
  // Post inc I
  add I, v1
  // Note that we did so
  add v2, 1
  // Ignoring what happens with no closing ] here
  se v0, 0x5D
  jp closing_loop

  // We've found a closing ']'
  // Decrement since the main loop's get cmd will inc it too
  sub v2, v1

  call get_instr_offset
  add v0, v2
  call store_instr_offset
  jp entry

handle_close_square:
  // If value at data pointer is non 0, skip backward to cmd after '['
  call get_data_ptr
  ld v0, [I]

  // If it's not 0 move to next command
  sne v0, 0
  jp entry

  // Otherwise search backwards for a '['
  // Since we can't decrement I directly, use the offset and apply manually
  call get_instr_offset
  // Copy offset into v1 as we need v0 to load commands
  ld v1, v0
  // For decrementing the offset
  ld v2, 1

open_loop:
  // pre dec since we know the current cmd will start as ']'
  sub v1, v2
  ld I, program
  add I, v1
  // get cmd
  ld v0, [I]
  // If we got a '['
  se v0, 0x5B
  jp open_loop

  // We want the cmd after the '['
  // but the usual get cmd func does the increment for us
  // so no increment here

  //Store the new offset
  ld v0, v1
  call store_instr_offset
  jp entry

handle_end_prog:
  // Just spin
  brk
  jp handle_end_prog

store_data_offset:
  // Write data offset from v0 into memory
  ld I, data_offset
  ld [I], v0
  ret

get_data_offset:
  // Load data offset into v0
  ld I, data_offset
  ld v0, [I]
  ret

get_data_ptr:
  // Load data pointer into I
  call get_data_offset
  ld I, data
  add I, v0
  ret

get_instr_ptr:
  ld I, instr_offset
  ld v0, [I]
  ld I, program
  add I, v0
  ret

get_instr_offset:
  ld I, instr_offset
  ld v0, [I]
  ret

store_instr_offset:
  ld I, instr_offset
  ld [I], v0
  ret

get_command:
  // Get instr pointer offset
  ld I, instr_offset
  ld v0, [I]
  // Increment
  add v0, 1
  // Store in case we have to use data
  ld [I], v0
  // Load base of program
  ld I, program
  // Offset to current command
  add I, V0
  // Read command from memory
  ld v0, [I]
  ret

"""

def generate_asm(prog):
  return interpreter_asm.format(
      prog=pad_program(program_to_words(prog)),
      data="\n".join(['.word 0x0000']*(256/2)),
      handler_switch=generate_handler_switch(),
      )

if __name__ == "__main__":
  import doctest
  doctest.testmod()
  with open('brain.s', 'w') as f:
    f.write(generate_asm('+++++>+++[-<->]<.'))
