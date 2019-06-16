import logging
import glob
import sys

from ctypes import c_uint8, c_uint16, c_int8

fmt = '[{levelname:7s}] {name:s}: {message:s}'
logger = logging.getLogger(__name__)

class VMError(Exception):
    pass

class VM:
    instructions_sizes = {
        0x0: 2, 0x1: 2, 0x2: 2, 0x3: 1,
        0x4: 2, 0x5: 2, 0x6: 2, 0x7: 2,
        0x8: 2, 0x9: 2, 0xA: 2, 0xB: 1,
        0xC: 1,
    }

    def __init__(self, banks=16, bank_size=4096):
        logger.debug("Initializing VM")
        logger.debug("Memory banks: %d", banks)
        logger.debug("Bank size: %d bytes", bank_size)

        self.instruction_decoders = {
            0x0: self._jump,
            0x1: self._jump_if_zero,
            0x2: self._jump_if_negative,
            0x3: self._control,
            0x4: self._sum,
            0x5: self._subtract,
            0x6: self._multiply,
            0x7: self._divide,
            0x8: self._load,
            0x9: self._store,
            0xA: self._subroutine_call,
            0xB: self._os_call,
            0xC: self._io,
        }

        self.main_memory = [[c_uint8(0) for i in range(bank_size)] for j in range(banks)] # 16 banks of 4096 bytes
        self._ri = c_uint16(0)
        self._ci = c_uint16(0)
        self._acc = c_int8(0)

        self._cb = c_uint8(0)
        self.indirect_mode = False
        self.running = True

        self.io_devices = [
            (sys.stdin.buffer, sys.stdout.buffer),
            [None, None],
            [None, None],
            [None, None],
        ]

        self.loading = False

        logger.debug('Loading loader')
        with open('system/loader.obj.0', 'r') as f:
            bs = f.read().split()

            addr = int(bs[0], 16) << 8 | int(bs[1], 16)
            s = int(bs[2], 16)
            logger.debug('Initial loader save address: %04X', addr)
            logger.debug('Amount of bytes: %02X', s)

            for b in bs[3:3+s]:
                self.main_memory[addr >> 12][addr & 0xFFF].value = int(b, 16)
                addr += 1
        logger.debug('Loader loaded')


    @property
    def current_instruction(self):
        return self._ri.value

    @current_instruction.setter
    def current_instruction(self, value):
        self._ri.value = value

    @property
    def instruction_counter(self):
        return self._ci.value

    @instruction_counter.setter
    def instruction_counter(self, value):
        self._ci.value = value

    @property
    def accumulator(self):
        return self._acc.value

    @accumulator.setter
    def accumulator(self, value):
        self._acc.value = value
        logger.debug('Accumulator: %+03X (%d)', self._acc.value, self._acc.value)

    @property
    def current_bank(self):
        return self._cb.value

    @current_bank.setter
    def current_bank(self, value):
        self._cb.value = value

    def load(self, filen):
        self.loading = True
        logger.debug('Loading file to memory')
        for fn in glob.glob(filen + '.bin.*'):
            logger.debug('Changing file - %s', fn)
            self.io_devices[1][0] = open(fn, 'rb')
            self.instruction_counter = 0x0000 # loader starts at 0

            self.running = True
            while self.running:
                self.fetch()
                self.decode_execute()

            self.io_devices[1][0].close()
            self.io_devices[1][0] = None

        self.loading = False

    def run(self, step=False):
        self.instruction_counter = self.main_memory[0][0x022].value << 8 | self.main_memory[0][0x023].value
        self.running = True
        while self.running:
            self.fetch()
            self.decode_execute()
            if step:
                input()

    def fetch(self):
        logger.debug('Fetching Instruction %04X', self.instruction_counter)
        logger.debug('Bank %d - PC: %X', self.current_bank, self.instruction_counter)
        instruction_type = self.main_memory[self.current_bank][self.instruction_counter].value >> 4
        instruction_size = self.instructions_sizes[instruction_type]

        logger.debug('Instruction type 0x%X - %d byte(s)', instruction_type, instruction_size)

        if instruction_size == 1:
            # Most significant byte
            self.current_instruction = self.main_memory[self.current_bank][self.instruction_counter].value << 8
        elif instruction_size == 2:
            self.current_instruction = (self.main_memory[self.current_bank][self.instruction_counter].value << 8) | \
                self.main_memory[self.current_bank][self.instruction_counter + 1].value

        logger.debug('Complete instruction: 0x%04X', self.current_instruction)

        self.instruction_counter += instruction_size

    def decode_execute(self):
        logger.debug('Decoding and Executing Instruction')
        instruction_type = self.current_instruction >> 12 # First nibble

        if instruction_type not in self.instruction_decoders:
            raise VMError('Bad instruction at address 0x{:01X}{:03X}'.format(self.current_bank, self.instruction_counter))

        self.instruction_decoders[instruction_type]()

    def update_pc(self, operand):
        if self.indirect_mode:
            addr = self.main_memory[self.current_bank][operand].value << 8 | self.main_memory[self.current_bank][operand + 1].value
            self.instruction_counter = addr & 0xFFF
            self.current_bank = addr >> 12
        else:
            self.instruction_counter = operand

        self.indirect_mode = False

    def get_indirect_value(self, operand):
        if self.indirect_mode:
            addr = self.main_memory[self.current_bank][operand].value << 8 | self.main_memory[self.current_bank][operand + 1].value
            addr &= 0xFFF
        else:
            addr = operand

        self.indirect_mode = False

        return self.main_memory[self.current_bank][addr].value

    def _jump(self):
        operand = self.current_instruction & 0xFFF
        self.update_pc(operand)

    def _jump_if_zero(self):
        if self.accumulator != 0:
            return

        operand = self.current_instruction & 0xFFF
        self.update_pc(operand)

    def _jump_if_negative(self):
        if self.accumulator < 0:
            return

        operand = self.current_instruction & 0xFFF
        self.update_pc(operand)

    def _control(self):
        operand = (self.current_instruction & 0x0F00) >> 8
        logger.debug('Control Operation {:d}'.format(operand))

        if operand == 0: # Halt Machine
            logger.warning('Machine Halted! Press ctrl+C to interrupt execution!')
            try:
                while True:
                    pass
            except KeyboardInterrupt:
                self.running = False

        elif operand == 1: # Return from Interrupt
            pass

        elif operand == 2: # Indirect
            logger.debug('Activating Indirect Mode')
            self.indirect_mode = True

        else:
            logger.warning('Unknown Control operation at 0x{:01X}{:03X}'.format(self.current_bank, self.instruction_counter))

    def _sum(self):
        operand = self.current_instruction & 0xFFF
        self.accumulator += self.get_indirect_value(operand)

    def _subtract(self):
        operand = self.current_instruction & 0xFFF
        self.accumulator -= self.get_indirect_value(operand)

    def _multiply(self):
        operand = self.current_instruction & 0xFFF
        self.accumulator *= self.get_indirect_value(operand)

    def _divide(self):
        operand = self.current_instruction & 0xFFF
        self.accumulator //= self.get_indirect_value(operand)

    def _load(self):
        operand = self.current_instruction & 0xFFF
        self.accumulator = self.get_indirect_value(operand)

    def _store(self):
        operand = self.current_instruction & 0xFFF

        if self.indirect_mode:
            addr = self.main_memory[self.current_bank][operand].value << 8 | self.main_memory[self.current_bank][operand + 1].value
            if addr < 0x0100 and not self.loading:
                logger.warning('Trying to write to memory area before 0x0100')
            bank = addr >> 12
            addr &= 0xFFF
        else:
            bank = self.current_bank
            addr = operand

        self.indirect_mode = False

        logger.debug('Writing to memory bank %d, address 0x%03X, value %02X', bank, addr, self.accumulator)
        self.main_memory[bank][addr].value = self.accumulator

    def _subroutine_call(self):
        operand = self.current_instruction & 0xFFF
        next_instr = self.instruction_counter

        self.main_memory[self.current_bank][operand].value = next_instr >> 8
        self.main_memory[self.current_bank][operand + 1].value = next_instr & 0xFF

        self.instruction_counter = operand + 2

    def _os_call(self):
        operand = (self.current_instruction & 0x0F00) >> 8 # last nibble

        logger.debug('Receive OS call %1X', operand)

        if operand == 0b0000: # Dump current state to stdout
            uacc = c_uint8(self._acc.value).value
            sacc = self._acc.value

            print('-- Current VM State')
            print('ACC => {0: #05x} | {0: 04d} | {1:#04x} | {1:03d}'.format(sacc, uacc))
            print('CI  => {0: #05x} | {0: 04d}'.format(self.instruction_counter))
        elif operand == 0b1111: # Finish execution
            self.running = False
        else:
            logger.warning('OS call %01X not implemented, skipping', operand)

    def _io(self):
        operand = (self.current_instruction & 0x0F00) >> 8 # last nibble
        op_type = operand >> 2
        device = operand & 0x3

        if op_type == 0b00: # Get data
            if self.io_devices[device][0] is None:
                raise VMError('Tried to get data from inexistent device')
            try:
                self.accumulator = ord(self.io_devices[device][0].read(1))
            except TypeError:
                logger.warning('TypeError!')
                pass
        elif op_type == 0b01: # Put data
            if self.io_devices[device][1] is None:
                raise VMError('Tried to put data on inexistent device')
            v = self.accumulator.to_bytes(1, 'big')
            self.io_devices[device][1].write(v)
        elif op_type == 0b10: # Enable Interrupt
            pass
        elif op_type == 0b11: # Disable Interrupt
            pass