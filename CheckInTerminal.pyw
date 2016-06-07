#!/usr/bin/env python3

# TermTest is a test environment for a serial terminal.
# Copyright (C) 2015  Werner Meier <wene83@gmx.ch>
#
# This license (GPL v3) is applied because of the license terms of a
# library (PyQt) I use in this project.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from PyQt5.QtCore import *
from PyQt5.QtSerialPort import *
from PyQt5.QtWidgets import *
from Terminal import Terminal
from datetime import datetime


class Form(QWidget):
    def __init__(self, parent=None):
        super(Form, self).__init__(parent)
        layout = QVBoxLayout(self)

        # restore saved settings
        self.settings = QSettings("Wene", "CheckInTerminal")
        self.move(self.settings.value("Position", QPoint(10, 10), type=QPoint))
        self.resize(self.settings.value("Size", QSize(100, 100), type=QSize))

        # define port selection layout and widgets
        lay_select = QHBoxLayout()
        layout.addLayout(lay_select)
        self.port_selector = QComboBox()
        self.port_selector.currentIndexChanged.connect(self.port_selected)
        self.speed_selector = QComboBox()
        # enable resizing after widget gets first shown
        self.speed_selector.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.speed_selector.currentIndexChanged.connect(self.speed_selected)
        self.btn_connect = QPushButton("&Connect")
        self.btn_connect.setEnabled(False)
        self.btn_connect.clicked.connect(self.connect_to_serial)
        lay_select.addWidget(self.port_selector)
        lay_select.addWidget(self.speed_selector)
        lay_select.addWidget(self.btn_connect)
        lay_select.addStretch()
        self.fill_port_selector()

        # Create message window
        self.inbox = QTextEdit()
        self.inbox.setReadOnly(True)
        layout.addWidget(self.inbox)

        # define serial port
        self.serial_port = QSerialPort()

        self.timer = QTimer()
        self.timer.setInterval(1000)

    # search for available serial ports and fill the QComboBox
    def fill_port_selector(self):
        self.port_selector.clear()
        self.port_selector.addItem("Select port...")
        port_list = QSerialPortInfo.availablePorts()
        for port in port_list:
            assert isinstance(port, QSerialPortInfo)
            port_name = port.portName() + " (" + port.manufacturer() + " / " + port.description() + ")"
            self.port_selector.addItem(port_name, port)

        # append dummy port for local simulation
        port_name = "/dev/pts/X (Dummy)"
        port = "Dummy"  # String to identify the dummy port
        self.port_selector.addItem(port_name, port)

        # restore last time selected port
        port_setting = self.settings.value("Port", type=int)
        speed_setting = self.settings.value("Speed", type=int)
        if isinstance(port_setting, int):
            self.port_selector.setCurrentIndex(port_setting)
        if isinstance(speed_setting, int):
            self.speed_selector.setCurrentIndex(speed_setting)

    # this slot is called by selecting another serial port -> list the available speed settings
    def port_selected(self):
        self.speed_selector.clear()
        port = self.port_selector.currentData()
        self.speed_selector.addItem("Speed...")
        if isinstance(port, QSerialPortInfo):  # the first and the dummy aren't QSerialPortInfo. They're just text.
            speed_list = port.standardBaudRates()
            for speed in speed_list:
                self.speed_selector.addItem(str(speed), speed)
        elif isinstance(port, str):  # If it's the dummy, set speed also to dummy
            if port == "Dummy":
                self.speed_selector.addItem("Dummy", 0)

    # This slot is called by selecting a speed. If valid the btn_connect gets enabled.
    def speed_selected(self):
        speed = self.speed_selector.currentData()
        if isinstance(speed, int):
            self.btn_connect.setEnabled(True)
        else:
            self.btn_connect.setEnabled(False)

    # establish serial connection with chosen settings
    def connect_to_serial(self):
        port = self.port_selector.currentData()
        speed = self.speed_selector.currentData()
        self.inbox.append("connecting...")
        if isinstance(port, QSerialPortInfo) and isinstance(speed, int):
            self.serial_port.setPort(port)
            self.serial_port.setBaudRate(speed)
            connected = self.serial_port.open(QIODevice.ReadWrite)
            self.inbox.append("Connection: " + str(connected))
            if not connected:
                self.inbox.append("Error: " + self.serial_port.errorString())
                return

        # local test dummy for use with socat
        # [socat -d -d pty,raw,echo=0,user=<username> pty,raw,echo=0,user=<username>]
        elif isinstance(port, str) and port == "Dummy":
            self.serial_port.setPortName("/dev/pts/3")  # replace port number when needed
            connected = self.serial_port.open(QIODevice.ReadWrite)
            self.inbox.append("Connection: " + str(connected))
            if not connected:
                self.inbox.append("Error: " + self.serial_port.errorString())
                return
                # connection from the other side is made by [screen /dev/pts/3]
        else:
            return

        self.port_selector.setEnabled(False)
        self.speed_selector.setEnabled(False)
        self.btn_connect.setEnabled(False)
        self.timer.timeout.connect(self.clock)
        self.timer.start()

        self.terminal = Terminal(self.serial_port)
        sequence = bytearray()
        sequence += b'Willkommen am CoSin 2016'
        self.terminal.write_big(9, 5, sequence)
        self.terminal.set_cursor_pos(24, 7)
        self.terminal.set_style('underscore')
        self.terminal.write(b'Projekt "CheckIn Terminal" Ruum42')
        self.terminal.set_cursor_pos(1, 12)
        self.terminal.set_style('normal')
        self.terminal.set_style('bold')
        self.terminal.write(b'Nickname: [               ]')
        self.terminal.set_style('normal')
        self.terminal.set_cursor_pos(12, 12)

    def clock(self):
        x, y = self.terminal.get_cursor_pos()
        self.terminal.set_cursor_pos(70, 1)
        hour = datetime.now().hour
        minute = datetime.now().minute
        second = datetime.now().second
        time = bytearray()
        time += bytearray(str(hour).zfill(2), encoding='ascii')
        time += b':'
        time += bytearray(str(minute).zfill(2), encoding='ascii')
        time += b':'
        time += bytearray(str(second).zfill(2), encoding='ascii')
        self.terminal.write(time)
        self.terminal.set_cursor_pos(x, y)

    # save settings
    def closeEvent(self, QCloseEvent):
        self.settings.setValue("Position", self.pos())
        self.settings.setValue("Size", self.size())
        self.serial_port.close()
        self.settings.setValue("Port", self.port_selector.currentIndex())
        self.settings.setValue("Speed", self.speed_selector.currentIndex())


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)

    translator = QTranslator()
    lib_path = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
    translator.load("qt_en.qm", lib_path)
    translator.load("qtbase_en.qm", lib_path)
    app.installTranslator(translator)

    window = Form()
    window.show()

    sys.exit(app.exec_())
