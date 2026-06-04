class LcdApi:
    LCD_CLR = 0x01
    LCD_HOME = 0x02
    LCD_ENTRY_MODE = 0x04
    LCD_DISPLAY_CTRL = 0x08
    LCD_CURSOR_SHIFT = 0x10
    LCD_FUNCTION_SET = 0x20
    LCD_CGRAM_ADDR = 0x40
    LCD_DDRAM_ADDR = 0x80

    ENTRY_RIGHT = 0x00
    ENTRY_LEFT = 0x02
    ENTRY_SHIFT_INC = 0x01
    ENTRY_SHIFT_DEC = 0x00

    DISPLAY_ON = 0x04
    DISPLAY_OFF = 0x00
    CURSOR_ON = 0x02
    CURSOR_OFF = 0x00
    BLINK_ON = 0x01
    BLINK_OFF = 0x00

    DISPLAY_MOVE = 0x08
    CURSOR_MOVE = 0x00
    MOVE_RIGHT = 0x04
    MOVE_LEFT = 0x00

    _8BIT_MODE = 0x10
    _4BIT_MODE = 0x00
    _2LINE = 0x08
    _1LINE = 0x00
    _5x10DOTS = 0x04
    _5x8DOTS = 0x00

    def __init__(self, num_lines, num_columns):  # ✅ FIXED: _init_ diubah menjadi __init__
        self.num_lines = num_lines
        self.num_columns = num_columns
        self.cursor_x = 0
        self.cursor_y = 0
        self.init_lcd()

    def init_lcd(self):
        raise NotImplementedError

    def clear(self):
        self.hal_write_command(self.LCD_CLR)
        self.hal_write_command(self.LCD_HOME)
        self.cursor_x = 0
        self.cursor_y = 0

    def move_to(self, cursor_x, cursor_y):
        self.cursor_x = cursor_x
        self.cursor_y = cursor_y
        addr = cursor_x & 0x3F
        if cursor_y & 1:
            addr += 0x40
        if cursor_y & 2:
            addr += 0x14
        self.hal_write_command(self.LCD_DDRAM_ADDR | addr)

    def putstr(self, string):
        for char in string:
            if char == '\n':
                self.cursor_y += 1
                if self.cursor_y >= self.num_lines:
                    self.cursor_y = 0
                self.move_to(0, self.cursor_y)
            else:
                self.hal_write_data(ord(char))
                self.cursor_x += 1
                if self.cursor_x >= self.num_columns:
                    self.cursor_x = 0
                    self.cursor_y += 1
                    if self.cursor_y >= self.num_lines:
                        self.cursor_y = 0
                    self.move_to(self.cursor_x, self.cursor_y)

    def hal_write_command(self, cmd):
        raise NotImplementedError

    def hal_write_data(self, data):
        raise NotImplementedError