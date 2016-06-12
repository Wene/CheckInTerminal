#!/usr/bin/env python3

from PyQt5.QtCore import *
from PyQt5.QtSerialPort import *


class Terminal(QObject):

    buttonPressed = pyqtSignal(str)
    gotCoordinates = pyqtSignal(int, int)
    nameEntered = pyqtSignal(str)

    def __init__(self, serial_port, parent=None):
        super(Terminal, self).__init__(parent)
        assert(isinstance(serial_port, QSerialPort))
        self.port = serial_port
        self.port.readyRead.connect(self.read_serial)
        self.set_style('normal')
        self.clear_screen()
        self.set_cursor_pos(1, 1)

        self.buffer = bytearray()
        self.nickname = bytearray()

        self.last_known_X = 0
        self.last_known_Y = 0

        self.input_X = 12
        self.input_Y = 12

        self.buttonPressed.connect(self.handle_key)
        self.gotCoordinates.connect(self.set_last_known_coordinates)

    def set_last_known_coordinates(self, x, y):
        self.last_known_X = x
        self.last_known_Y = y

    def get_last_known_coordinates(self):
        x = self.last_known_X
        y = self.last_known_Y
        return x, y

    def set_cursor_to_input(self):
        self.set_cursor_pos(self.input_X, self.input_Y)

    def read_serial(self):
        data = self.port.read(self.port.bytesAvailable())
        self.buffer += data
        text = bytearray()
        # search check buffer for escape sequence
        pos = 0
        delimiter = b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ~'
        numbers = b'0123456789'
        parameters = list()
        while pos < len(self.buffer):
            if self.buffer[pos] == 27:                   # begin of escape sequence
                begin = pos
                end = pos
                if len(self.buffer) > pos+1 and self.buffer[pos+1] == ord('['):       # second character of escape sequence
                    pos += 2
                    while len(self.buffer) > pos:
                        num = bytearray(b'')
                        while len(self.buffer) > pos and self.buffer[pos] in numbers:
                            num.append(self.buffer[pos])
                            pos += 1
                        if len(num) > 0:
                            parameters.append(int(num))
                        if len(self.buffer) > pos and self.buffer[pos] == 59:          # ';'
                            pos += 1
                            continue
                        else:
                            break

                    if pos < len(self.buffer) and self.buffer[pos] in delimiter:       # complete sequence found
                        command = self.buffer[pos]
                        end = pos + 1
                        # remove escape sequence from buffer
                        self.buffer = self.buffer[:begin] + self.buffer[end:]
                    else:                                   # incomplete sequence - wait for completion
                        break

                    if command == ord('A'):
                        self.buttonPressed.emit('up')
                    elif command == ord('B'):
                        self.buttonPressed.emit('down')
                    elif command == ord('C'):
                        self.buttonPressed.emit('right')
                    elif command == ord('D'):
                        self.buttonPressed.emit('left')
                    elif command == ord('R'):                   # Cursor Position Report
                        if len(parameters) >= 2:
                            x = parameters[1]
                            y = parameters[0]
                            self.gotCoordinates.emit(x, y)
                pos += 1

            elif len(self.buffer) > 0:
                character = self.buffer.pop(0)
                if character == 13:
                    nick = str(self.nickname, encoding='ascii')
                    self.nameEntered.emit(nick)
                    self.nickname.clear()
                    self.set_cursor_pos(12, 12)
                    self.write(b'                              ')
                    self.set_cursor_pos(12, 12)
                    self.input_X = 12
                elif character == 127:  #
                    self.buttonPressed.emit('left')
                elif character < 32:
                    pass
                else:
                    text.append(character)

        if len(text) > 0 and len(self.nickname) < 30:
            self.write(text)
            self.nickname += text
            self.input_X = 12 + len(self.nickname)

    def handle_key(self, key):
        if key == 'left':
            if len(self.nickname) > 0:
                self.write(b'\x1b[D \x1b[D')
                self.nickname.pop()
                self.input_X = 12 + len(self.nickname)
        if key == 'right':
            if len(self.nickname) < 30:
                self.write(b'\x1b[C')
                self.nickname += b' '
                self.input_X = 12 + len(self.nickname)

    def clear_screen(self):
        self.port.write(b'\x1b[2J')

    def set_cursor_pos(self, x, y):
        sequence = bytearray(b'\x1b[')
        sequence += self.int_to_bytearray(y)
        sequence += b';'
        sequence += self.int_to_bytearray(x)
        sequence += b'H'
        self.port.write(sequence)

    def request_cursor_pos(self):
        self.write(b'\x1b[6n')

    def write_big(self, x, y, text):
        sequence = bytearray(b'\x1b#3')     # Top half of double height font
        self.set_cursor_pos(x, y)
        sequence += text
        self.write(sequence)
        self.set_cursor_pos(x, y + 1)
        sequence.clear()
        sequence += b'\x1b#4'               # Bottom half of double height font
        sequence += text
        self.write(sequence)

    def write(self, text):
        self.port.write(text)

    def set_style(self, style):
        sequence = bytearray(b'\x1b[')
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
