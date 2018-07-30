#!/usr/bin/python3

import buspirate as bp
import re
import serial
import struct
import time


class AS726x_I2C:

    ADDR = 0x49
    SENSORTYPE_AS7261 = 0x3D
    SENSORTYPE_AS7262 = 0x3E
    SENSORTYPE_AS7263 = 0x3F
    DEVICE_TYPE = 0x00
    HW_VERSION = 0x01
    CONTROL_SETUP = 0x04
    INT_T = 0x05
    DEVICE_TEMP = 0x06
    LED_CONTROL = 0x07
    STATUS_REG = 0x00
    WRITE_REG = 0x01
    READ_REG = 0x02
    TX_VALID = 0x02
    RX_VALID = 0x01
    DEBUG = False

    def __init__(self, port: str):
        self.addr = self.ADDR
        self.i2c = bp.I2C(port, bp.I2C_SPEED_400KHZ)
        self.i2c.set_fast(1)
        self.hard_reset()
        self.ver = self.read_reg(self.HW_VERSION)
        if (self.ver != self.SENSORTYPE_AS7262 and
           self.ver != self.SENSORTYPE_AS7263):
            raise IOError("Cannot communicate")
        self.set_bulb_current(0b00)
        self.set_bulb(0)
        self.set_indicator_current(0b11)
        self.set_indicator(0)
        self.set_gain(3)
        self.set_mode(3)

    def read_reg_(self, reg: int):
        # You need newer Buspirate FW for this to work:
        r = self.i2c.cmd_recv(self.addr, reg, 1)[0]
        # r = self.i2c.send(self.addr, [reg])
        # r = self.i2c.recv(self.addr, 1)[0]
        if self.DEBUG:
            print("RX %d=%d" % (reg, r))
        return r

    def write_reg_(self, reg: int, val: int):
        if self.DEBUG:
            print("TX %d=%d" % (reg, val))
        self.i2c.send(self.addr, [reg, val])

    def read_reg(self, reg: int):
        status = self.read_reg_(self.STATUS_REG)
        while status & self.RX_VALID:
            incoming = self.read_reg_(self.READ_REG)
            status = self.read_reg_(self.STATUS_REG)
        while status & self.TX_VALID != 0:
            status = self.read_reg_(self.STATUS_REG)
        self.write_reg_(self.WRITE_REG, reg)
        status = self.read_reg_(self.STATUS_REG)
        while status & self.RX_VALID == 0:
            status = self.read_reg_(self.STATUS_REG)
        incoming = self.read_reg_(self.READ_REG)
        return incoming

    def write_reg(self, reg: int, val: int):
        status = self.read_reg_(self.STATUS_REG)
        while status & self.TX_VALID != 0:
            status = self.read_reg_(self.STATUS_REG)
        self.write_reg_(self.WRITE_REG, reg | 0x80)
        status = self.read_reg_(self.STATUS_REG)
        while status & self.TX_VALID != 0:
            status = self.read_reg_(self.STATUS_REG)
        self.write_reg_(self.WRITE_REG, val)

    # 0: 12.5mA
    # 1: 25mA
    # 2: 50mA
    # 3: 100mA
    def set_bulb_current(self, current: int):
        if current > 0b11:
            current = 0b11
        value = self.read_reg(self.LED_CONTROL)
        value &= 0b11001111
        value |= (current << 4)
        self.write_reg(self.LED_CONTROL, value)

    def set_bulb(self, val: int):
        value = self.read_reg(self.LED_CONTROL)
        value &= ~(1 << 3)
        value |= (val << 3)
        self.write_reg(self.LED_CONTROL, value)

    def get_temperature(self):
        return self.read_reg(self.DEVICE_TEMP)

    # Max 8mA = 0b11
    def set_indicator_current(self, current: int):
        if current > 0b11:
            current = 0b11
        value = self.read_reg(self.LED_CONTROL)
        value &= 0b11111001
        value |= (current << 1)
        self.write_reg(self.LED_CONTROL, value)

    def set_indicator(self, val: int):
        value = self.read_reg(self.LED_CONTROL)
        value &= ~(1 << 0)
        value |= (val << 0)
        self.write_reg(self.LED_CONTROL, value)

    # Gain 0: 1x (power-on default)
    # Gain 1: 3.7x
    # Gain 2: 16x
    # Gain 3: 64x
    def set_gain(self, gain: int):
        if gain > 0b11:
            gain = 0b11
        value = self.read_reg(self.CONTROL_SETUP)
        value &= 0b11001111
        value |= (gain << 4)
        self.write_reg(self.CONTROL_SETUP, value)

    # Give this function a byte from 0 to 255.
    # Time will be 2.8ms * [integration value]
    def set_integration(self, val: int):
        self.write_reg(self.INT_T, val)

    def set_integration_ms(self, val: float):
        self.set_integration(int(val / 2.8))

    def measure(self):
        self.clear_data()
        self.set_mode(3)
        while not self.has_data():
            pass

    def get_channel(self, addr: int):
        data = self.read_reg(addr) << 8
        data |= self.read_reg(addr + 1)
        return data

    def get_calibrated(self, addr: int):
        return struct.unpack(
            ">f",
            struct.pack(
                "BBBB",
                self.read_reg(addr + 0),
                self.read_reg(addr + 1),
                self.read_reg(addr + 2),
                self.read_reg(addr + 3)))[0]

    def has_data(self):
        value = self.read_reg(self.CONTROL_SETUP)
        return value & (1 << 1)

    def clear_data(self):
        value = self.read_reg(self.CONTROL_SETUP)
        value &= ~(1 << 1)
        self.write_reg(self.CONTROL_SETUP, value)

    def soft_reset(self):
        value = self.read_reg(self.CONTROL_SETUP)
        value |= (1 << 7)
        self.write_reg(self.CONTROL_SETUP, value)
        time.sleep(1)

    # Reset must be wired to Buspirate CS
    def hard_reset(self):
        self.i2c.set_pin(0, 0)
        time.sleep(1)
        self.i2c.set_pin(1, 1)
        time.sleep(1)

    # Mode 0: Continuous reading of VBGY (7262) / STUV (7263)
    # Mode 1: Continuous reading of GYOR (7262) / RTUX (7263)
    # Mode 2: Continuous reading of all channels (power-on default)
    # Mode 3: One-shot reading of all channels
    def set_mode(self, mode: int):
        if mode > 0b11:
            mode = 0b11
        value = self.read_reg(self.CONTROL_SETUP)
        value &= 0b11110011
        value |= (mode << 2)
        self.write_reg(self.CONTROL_SETUP, value)

    def get_all_values(self):
        return [
            self.get_calibrated(0x14),
            self.get_calibrated(0x18),
            self.get_calibrated(0x1c),
            self.get_calibrated(0x20),
            self.get_calibrated(0x24),
            self.get_calibrated(0x28)]

class AS726x_SERIAL:

    DEBUG = False
    FLOAT = r"[-+]?\d*\.\d+|\d+"

    def __init__(self, port: str):
        self.ser = serial.Serial(port, 115200, timeout=1)
        self.chat("AT", "OK")
        self.chat("ATTCSMD=2", "OK")
        self.set_interval(255)

    def chat(self, tx: str, match: str):
        if tx is not None:
            tx += "\n"
            self.ser.write(tx.encode("utf-8"))
        rx = self.ser.read_until()
        rx = rx.decode("utf-8")
        m = re.match(match, rx)
        if m is None:
            raise IOError("Unexpected answer: %s" % rx)
        return m

    def measure(self):
        # If you enable double read, ser_interval to 1!
        # self.chat("ATBURST=2", "OK")
        # self.chat(None, r"(\d+), (\d+), (\d+), (\d+), (\d+), (\d+)")
        # r = self.chat(None, r"(\d+), (\d+), (\d+), (\d+), (\d+), (\d+)")
        self.chat("ATBURST=1", "OK")
        r = self.chat(None, r"(\d+), (\d+), (\d+), (\d+), (\d+), (\d+)")
        self.chat("ATBURST=0", ".*OK")
        return [int(r[i]) for i in range(1, 7)]

    # 0: 12.5mA
    # 1: 25mA
    # 2: 50mA
    # 3: 100mA
    def set_bulb_current(self, current: int):
        if current > 0b11:
            current = 0b11
        v = int(self.chat("ATLEDC", r"\d+OK")[1])
        v &= ~(3 << 4)
        v |= (current << 4)
        self.chat("ATLEDC=%d" % v, "OK")

    def set_bulb(self, val: int):
        if val != 0:
            val = 100
        self.chat("ATLED0=%d" % val, "OK")

    # Max 8mA = 0b11
    def set_indicator_current(self, current: int):
        if current > 0b11:
            current = 0b11
        v = int(self.chat("ATLEDC", r"\d+OK")[1])
        v &= ~(3 << 0)
        v |= (current << 0)
        self.chat("ATLEDC=%d" % v, "OK")

    # Gain 0: 1x (power-on default)
    # Gain 1: 3.7x
    # Gain 2: 16x
    # Gain 3: 64x
    def set_gain(self, gain: int):
        if gain > 0b11:
            gain = 0b11
        self.chat("ATGAIN=%d" % gain, "OK")

    # Give this function a byte from 0 to 255.
    # Time will be 2.8ms * [integration value]
    def set_integration(self, val: int):
        self.chat("ATINTTIME=%d" % val, "OK")

    def set_integration_ms(self, val: float):
        self.set_integration(int(val / 2.8))

    def set_interval(self, val: int):
        self.chat("ATINTRVL=%d" % val, "OK")

    def soft_reset(self):
        self.chat("ATSRST", "OK")

    def get_temperature(self):
        return float(self.chat("ATTEMP", self.FLOAT + "OK")[1])

    def get_XYZ(self):
        r = self.chat("ATXYZC", ", ".join((self.FLOAT,) * 3) + "OK")
        return [float(r[i]) for i in range(1, 4)]

    def get_lux(self):
        return float(self.chat("ATLUXC", self.FLOAT + "OK")[1])

    def get_cct(self):
        return float(self.chat("ATCCTC", self.FLOAT + "OK")[1])

    def get_xy(self):
        r = self.chat("ATSMALLXYC", ", ".join((self.FLOAT,) * 2) + "OK")
        return [float(r[i]) for i in range(1, 3)]

    def get_uv(self):
        r = self.chat("ATUVPRIMEC", ", ".join((self.FLOAT,) * 4) + "OK")
        return [float(r[i]) for i in range(1, 5)]

    def get_duv(self):
        return float(self.chat("ATDUVC", self.FLOAT + "OK")[1])

    def get_cdata(self):
        r = self.chat("ATCDATA", ", ".join((self.FLOAT,) * 6) + "OK")
        return [float(r[i]) for i in range(1, 7)]


as726x = AS726x_SERIAL("/dev/ttyUSB0")
# as726x.set_bulb(1)
print(as726x.measure())
# print(as726x.get_all_values())
# as726x.set_bulb(0)
