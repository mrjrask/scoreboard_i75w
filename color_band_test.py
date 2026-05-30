"""Color-band diagnostic for Pimoroni Interstate 75 W (64x64 HUB75).

Copy this file to your Interstate 75 W and run it with MicroPython to verify
that the panel can render RGB colors.  It intentionally uses the PicoGraphics
API exposed by ``Interstate75.display`` because recent Pimoroni firmware does
not expose a ``hub75.set_rgb(...)`` method.
"""

import time

from interstate75 import Interstate75, DISPLAY_INTERSTATE75_64X64

WIDTH = 64
HEIGHT = 64

# Colors used by the scoreboard temperature bands from coldest to warmest.
COLOR_BANDS = (
    ("<0", (209, 0, 184)),
    ("0", (160, 0, 160)),
    ("10", (122, 51, 183)),
    ("20", (58, 58, 230)),
    ("30", (28, 147, 232)),
    ("40", (0, 176, 80)),
    ("50", (154, 208, 75)),
    ("60", (255, 204, 0)),
    ("70", (243, 154, 68)),
    ("80", (255, 26, 26)),
    ("90", (224, 0, 0)),
    ("100", (204, 0, 0)),
)


class MatrixCanvas:
    """Small drawing helper backed by the Interstate75 PicoGraphics display."""

    def __init__(self):
        self.i75 = Interstate75(display=DISPLAY_INTERSTATE75_64X64)
        self.graphics = self.i75.display
        self._pen_cache = {}
        self.black = self.pen(0, 0, 0)

    def pen(self, r, g, b):
        key = (r, g, b)
        if key not in self._pen_cache:
            self._pen_cache[key] = self.graphics.create_pen(r, g, b)
        return self._pen_cache[key]

    def clear(self):
        self.graphics.set_pen(self.black)
        self.graphics.clear()

    def pixel(self, x, y, color):
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            self.graphics.set_pen(self.pen(*color))
            self.graphics.pixel(x, y)

    def fill_rect(self, x, y, width, height, color):
        self.graphics.set_pen(self.pen(*color))
        self.graphics.rectangle(x, y, width, height)

    def text(self, value, x, y, color, scale=1):
        self.graphics.set_pen(self.pen(*color))
        self.graphics.text(str(value), x, y, scale=scale)

    def update(self):
        self.i75.update()


def color_band_test():
    canvas = MatrixCanvas()
    band_height = HEIGHT // len(COLOR_BANDS)
    extra_pixels = HEIGHT % len(COLOR_BANDS)
    y = 0

    canvas.clear()
    for index, (label, color) in enumerate(COLOR_BANDS):
        height = band_height + (1 if index < extra_pixels else 0)
        canvas.fill_rect(0, y, WIDTH, height, color)
        text_color = (0, 0, 0) if index >= 6 else (255, 255, 255)
        canvas.text(label, 1, y, text_color)
        y += height
    canvas.update()


color_band_test()

while True:
    time.sleep(1)
