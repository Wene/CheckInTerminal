#!/usr/bin/env python3

from PyQt5.QtCore import *
from PyQt5.QtSerialPort import *


class Terminal:
    def __init__(self, serial_port):
        assert(isinstance(serial_port, QSerialPort))
        self.port = serial_port
        self.port.readyRead.connect(self.read_serial)
        self.set_style('normal')
        self.clear_screen()
        self.set_cursor_pos(1, 1)

        self.buffer = bytearray()
        self.command = bytearray()

    def read_serial(self):
        data = self.port.read(self.port.bytesAvailable())
        self.buffer += data
        # search check buffer for escape sequence
        pos = 0
        while pos < len(self.buffer):
            if self.buffer[pos:pos+2] == b'\x1b[':      # begin of escape sequence
                begin = pos
                end = pos
                if self.buffer[pos+2:pos+3] == b'A':
                    self.port.write(b'up')
                    end = pos + 4
                if self.buffer[pos+2:pos+3] == b'B':
                    self.port.write(b'down')
                    end = pos + 4
                if self.buffer[pos+2:pos+3] == b'C':
                    self.port.write(b'right')
                    end = pos + 4
                if self.buffer[pos+2:pos+3] == b'D':
                    self.port.write(b'left')
                    end = pos + 4
                self.buffer = self.buffer[:begin] + self.buffer[end:]
            pos += 1


    def clear_screen(self):
        sequence = bytearray()
        sequence.append(27)
        sequence += b'[2J'          # Clear Screen
        self.port.write(sequence)

    def set_cursor_pos(self, x, y):
        sequence = bytearray()
        sequence.append(27)
        sequence += b'['
        sequence += self.int_to_bytearray(y)
        sequence += b';'
        sequence += self.int_to_bytearray(x)
        sequence += b'H'
        self.port.write(sequence)

    def get_cursor_pos(self):
        self.port.readyRead.disconnect()
        sequence = bytearray()
        sequence.append(27)
        sequence += b'[6n'
        self.port.write(sequence)
        sequence.clear()
        while True:
            self.port.waitForReadyRead(500)
            data = self.port.read(self.port.bytesAvailable())
            sequence += data
            if sequence[0] != 27:    # something went wrong...
                self.port.readyRead.connect(self.read_serial)
                return 0, 0                     # TODO: something doesn't work here...
            if sequence[-1] == ord(b'R'):
                break
        sequence.pop(0)  # esc
        sequence.pop(0)  # [
        sequence.pop()   # R
        string = sequence.decode('ascii')
        fields = string.split(';')
        y = int(fields.pop(0))
        x = int(fields.pop(0))
        self.port.readyRead.connect(self.read_serial)
        return x, y

    def write_big(self, x, y, text):
        sequence = bytearray()
        self.set_cursor_pos(x, y)
        sequence.append(27)
        sequence += b'#3'           # Top half of double height font
        sequence += text
        self.port.write(sequence)
        self.set_cursor_pos(x, y + 1)
        sequence.clear()
        sequence.append(27)
        sequence += b'#4'           # Bottom half of double height font
        sequence += text
        self.port.write(sequence)

    def write(self, text):
        self.port.write(text)

    def set_style(self, style):
        sequence = bytearray()
        sequence.append(27)
        sequence += b'['
        if style == 'bold':
            sequence += b'1'
        elif style == 'underscore':
            sequence += b'4'
        elif style == 'blink':
            sequence += b'5'
        elif style == 'invert':
            sequence += b'7'
        elif style == 'normal':
            sequence += b'0'
        else:
            return
        sequence += b'm'
        self.port.write(sequence)

    def int_to_bytearray(self, number):
        assert isinstance(number, int)
        string = str(number)
        text = bytearray()
        for character in string:
            text.append(ord(character))
        return text