from lcd_api import LcdApi
from machine import I2C
from time import sleep_ms

class I2cLcd(LcdApi):
    BACKLIGHT = 0x08
    ENABLE = 0x04
    RS = 0x01

    def __init__(self, i2c, i2c_addr, num_lines, num_columns):
        self.i2c = i2c
        self.i2c_addr = i2c_addr
        self.backlight = self.BACKLIGHT
        self._write_byte(0)
        sleep_ms(20)
        self._send_command(0x03)
        sleep_ms(5)
        self._send_command(0x03)
        sleep_ms(1)
        self._send_command(0x03)
        self._send_command(0x02)

        self._send_command(0x28)
        self._send_command(0x08)
        self._send_command(0x01)
        self._send_command(0x06)
        self._send_command(0x0C)

        super().__init__(num_lines, num_columns)

    def init_lcd(self):  # ✅ FIXED: Added empty implementation
        pass

    def hal_write_command(self, cmd):
        self._send_command(cmd)

    def hal_write_data(self, data):
        self._send_data(data)

    def _write_byte(self, data):
        self.i2c.writeto(self.i2c_addr, bytes([data | self.backlight]))

    def _toggle_enable(self, data):
        self._write_byte(data | self.ENABLE)
        sleep_ms(1)
        self._write_byte(data & ~self.ENABLE)
        sleep_ms(1)

    def _send_command(self, cmd):
        high = cmd & 0xF0
        low = (cmd << 4) & 0xF0
        self._write_4_bits(high)
        self._write_4_bits(low)

    def _send_data(self, data):
        high = data & 0xF0
        low = (data << 4) & 0xF0
        self._write_4_bits(high, self.RS)
        self._write_4_bits(low, self.RS)

    def _write_4_bits(self, data, mode=0):
        self._write_byte(data | mode)
        self._toggle_enable(data | mode)