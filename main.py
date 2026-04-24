"""Baseball scoreboard for Pimoroni Interstate 75 W (64x64 HUB75).

Copy this file to your Interstate 75 W as /main.py.
Optionally add /secrets.py with WIFI_SSID and WIFI_PASSWORD to enable
phone/browser control over Wi-Fi.
"""

import uasyncio as asyncio
import time
import math

try:
    import network
except ImportError:
    network = None

from interstate75 import Interstate75, DISPLAY_INTERSTATE75_64X64

DEVICE_HOSTNAME = "score"

try:
    import secrets

    BATTING_ORDER_ENABLED = bool(getattr(secrets, "BATTING_ORDER", True))
except Exception:
    BATTING_ORDER_ENABLED = True


class BME280TemperatureReader:
    def __init__(self):
        self._sensor = None
        self._available = None
        self._last_reading_f = None
        self._last_poll_ms = None
        self._poll_interval_ms = 5000

    def _init_sensor(self, i2c):
        if self._available is False:
            return
        if self._sensor is not None:
            return
        try:
            from breakout_bme280 import BreakoutBME280

            self._sensor = BreakoutBME280(i2c)
            self._available = True
            print("BME280 detected on QW/ST.")
        except Exception:
            self._sensor = None
            self._available = False
            print("BME280 not detected on QW/ST.")

    def get_temperature_f(self, i2c):
        now = time.ticks_ms()
        if self._last_poll_ms is not None and time.ticks_diff(now, self._last_poll_ms) < self._poll_interval_ms:
            return self._last_reading_f

        self._last_poll_ms = now
        self._init_sensor(i2c)
        if self._sensor is None:
            self._last_reading_f = None
            return None

        try:
            temperature_c, _, _ = self._sensor.read()
            self._last_reading_f = int(round((temperature_c * 9.0 / 5.0) + 32.0))
        except Exception:
            # Sensor disappeared or is not responding; hide value on display.
            self._sensor = None
            self._available = None
            self._last_reading_f = None
        return self._last_reading_f


class ScoreboardState:
    STATE_FILE = "scoreboard_state.json"
    STATE_TMP_FILE = "scoreboard_state.tmp"

    def __init__(self):
        self.team_a = "AWAY TEAM"
        self.team_b = "HOME TEAM"
        self.score_a = 0
        self.score_b = 0
        self.inning = 1
        self.inning_half = "top"
        self.balls = 0
        self.strikes = 0
        self.outs = 0
        self.text_colors = {
            "team_a_name": "#FFFFFF",
            "team_a_score": "#FFFFFF",
            "team_b_name": "#FFFFFF",
            "team_b_score": "#FFFFFF",
            "inning_label": "#FFFFFF",
            "inning_value": "#FFFFFF",
            "count_labels": "#FFFFFF",
        }
        self.brightness = 1.0
        self.batting_order_a = 9
        self.batting_order_b = 9
        self.current_batter_a = 0
        self.current_batter_b = 0
        self.load()

    def clamp(self):
        self.score_a = max(0, self.score_a)
        self.score_b = max(0, self.score_b)
        self.inning = max(1, self.inning)
        self.balls = min(max(0, self.balls), 3)
        self.strikes = min(max(0, self.strikes), 2)
        self.outs = min(max(0, self.outs), 2)
        if self.inning_half not in ("top", "bottom"):
            self.inning_half = "top"
        self.brightness = min(max(self.brightness, 0.05), 1.0)
        self.batting_order_a = min(max(int(self.batting_order_a), 1), 20)
        self.batting_order_b = min(max(int(self.batting_order_b), 1), 20)
        self.current_batter_a = int(self.current_batter_a) % self.batting_order_a
        self.current_batter_b = int(self.current_batter_b) % self.batting_order_b

    def _advance_half_inning(self):
        if self.inning_half == "top":
            self.inning_half = "bottom"
        else:
            self.inning_half = "top"
            self.inning += 1

    def _register_out(self):
        self.outs += 1
        self.balls = 0
        self.strikes = 0
        if self.outs >= 3:
            self.outs = 0
            self._advance_half_inning()

    def update(self, action):
        if action == "score_a_inc":
            self.score_a += 1
        elif action == "score_a_dec":
            self.score_a -= 1
        elif action == "score_b_inc":
            self.score_b += 1
        elif action == "score_b_dec":
            self.score_b -= 1
        elif action == "inning_inc":
            self.inning += 1
        elif action == "inning_dec":
            self.inning -= 1
        elif action == "half_toggle":
            self.inning_half = "bottom" if self.inning_half == "top" else "top"
        elif action == "balls_cycle":
            self.balls = (self.balls + 1) % 4
        elif action == "strikes_cycle":
            if self.strikes == 2:
                self._register_out()
            else:
                self.strikes += 1
        elif action == "outs_cycle":
            self._register_out()
        elif action == "reset":
            self.score_a = 0
            self.score_b = 0
            self.inning = 1
            self.inning_half = "top"
            self.balls = 0
            self.strikes = 0
            self.outs = 0
        elif action == "reset_scores":
            self.score_a = 0
            self.score_b = 0
        elif action == "reset_count":
            self.balls = 0
            self.strikes = 0
        elif action == "batter_a_advance":
            self.current_batter_a = (self.current_batter_a + 1) % self.batting_order_a
        elif action == "batter_b_advance":
            self.current_batter_b = (self.current_batter_b + 1) % self.batting_order_b
        elif action == "batter_current_advance":
            if self.inning_half == "top":
                self.current_batter_a = (self.current_batter_a + 1) % self.batting_order_a
            else:
                self.current_batter_b = (self.current_batter_b + 1) % self.batting_order_b
        self.clamp()
        self.save()

    def rename(self, team_a, team_b):
        self.team_a = (team_a or "AWAY TEAM").strip().upper()
        self.team_b = (team_b or "HOME TEAM").strip().upper()
        self.save()

    def update_text_colors(self, values):
        keys = (
            "team_a_name",
            "team_a_score",
            "team_b_name",
            "team_b_score",
            "inning_label",
            "inning_value",
            "count_labels",
        )
        for key in keys:
            value = values.get(key, "")
            if self._is_hex_color(value):
                self.text_colors[key] = value.upper()
        self.save()

    def set_brightness(self, value):
        try:
            brightness = float(value)
        except (TypeError, ValueError):
            return
        if not math.isfinite(brightness):
            return
        self.brightness = brightness
        self.clamp()
        self.save()

    def set_batting_order(self, team_a_count, team_b_count):
        try:
            self.batting_order_a = int(team_a_count)
            self.batting_order_b = int(team_b_count)
        except (TypeError, ValueError):
            return
        self.clamp()
        self.save()

    def _sync_filesystem(self):
        try:
            import os

            os.sync()
        except Exception:
            pass

    def to_dict(self):
        return {
            "team_a": self.team_a,
            "team_b": self.team_b,
            "score_a": self.score_a,
            "score_b": self.score_b,
            "inning": self.inning,
            "inning_half": self.inning_half,
            "balls": self.balls,
            "strikes": self.strikes,
            "outs": self.outs,
            "text_colors": self.text_colors,
            "brightness": self.brightness,
            "batting_order_a": self.batting_order_a,
            "batting_order_b": self.batting_order_b,
            "current_batter_a": self.current_batter_a,
            "current_batter_b": self.current_batter_b,
        }

    def load(self):
        try:
            import json

            with open(self.STATE_FILE, "r") as handle:
                saved = json.loads(handle.read())
        except Exception:
            self.clamp()
            return

        self.team_a = str(saved.get("team_a", self.team_a)).strip().upper() or "AWAY TEAM"
        self.team_b = str(saved.get("team_b", self.team_b)).strip().upper() or "HOME TEAM"
        self.score_a = int(saved.get("score_a", self.score_a))
        self.score_b = int(saved.get("score_b", self.score_b))
        self.inning = int(saved.get("inning", self.inning))
        self.inning_half = str(saved.get("inning_half", self.inning_half))
        self.balls = int(saved.get("balls", self.balls))
        self.strikes = int(saved.get("strikes", self.strikes))
        self.outs = int(saved.get("outs", self.outs))
        brightness = float(saved.get("brightness", self.brightness))
        if math.isfinite(brightness):
            self.brightness = brightness
        self.batting_order_a = int(saved.get("batting_order_a", self.batting_order_a))
        self.batting_order_b = int(saved.get("batting_order_b", self.batting_order_b))
        self.current_batter_a = int(saved.get("current_batter_a", self.current_batter_a))
        self.current_batter_b = int(saved.get("current_batter_b", self.current_batter_b))

        text_colors = saved.get("text_colors", {})
        if isinstance(text_colors, dict):
            for key, value in text_colors.items():
                if key in self.text_colors and self._is_hex_color(value):
                    self.text_colors[key] = value.upper()

        self.clamp()

    def save(self):
        try:
            import json
            import os

            with open(self.STATE_TMP_FILE, "w") as handle:
                handle.write(json.dumps(self.to_dict()))
            self._sync_filesystem()
            try:
                os.remove(self.STATE_FILE)
            except OSError:
                pass
            os.rename(self.STATE_TMP_FILE, self.STATE_FILE)
            self._sync_filesystem()
        except Exception as exc:
            print("State save failed:", exc)

    def _is_hex_color(self, value):
        if len(value) != 7 or value[0] != "#":
            return False
        for c in value[1:]:
            if c not in "0123456789abcdefABCDEF":
                return False
        return True


class MatrixRenderer:
    def __init__(self, state):
        self.state = state
        self.i75 = Interstate75(display=DISPLAY_INTERSTATE75_64X64)
        self.g = self.i75.display
        self.temperature_reader = BME280TemperatureReader()

        self.BLACK = self.g.create_pen(0, 0, 0)
        self.RED_HEX = "#FF2800"
        self.DIM_HEX = "#303030"
        self._pen_cache = {}
        self._pulse_pen_cache = {}
        self._pulse_steps = 12
        self._last_brightness = None
        self._apply_brightness()

    def _set_brightness_target(self, target, brightness):
        for method_name in ("set_brightness", "set_led_brightness", "set_backlight"):
            try:
                getattr(target, method_name)(brightness)
                return True
            except Exception:
                pass
        try:
            target.brightness = brightness
            return True
        except Exception:
            return False

    def _apply_brightness(self):
        # Pimoroni APIs vary by firmware version, so try a few options.
        for target in (self.i75, self.g):
            if self._set_brightness_target(target, self.state.brightness):
                return
        print("Warning: unable to apply brightness with available APIs.")

    def _pen_from_hex(self, color_hex):
        cache_key = (color_hex, self.state.brightness)
        if cache_key in self._pen_cache:
            return self._pen_cache[cache_key]
        scale = self.state.brightness
        r = int(int(color_hex[1:3], 16) * scale)
        g = int(int(color_hex[3:5], 16) * scale)
        b = int(int(color_hex[5:7], 16) * scale)
        pen = self.g.create_pen(r, g, b)
        self._pen_cache[cache_key] = pen
        return pen

    def _draw_count_row(self, y, label, count, max_count):
        s = self.state
        self.g.set_pen(self._pen_from_hex(s.text_colors["count_labels"]))
        self.g.text(label, 36, y - 3, scale=1)
        for i in range(max_count):
            self.g.set_pen(self._pen_from_hex(self.RED_HEX if i < count else self.DIM_HEX))
            self.g.circle(45 + i * 7, y, 2)

    def _right_aligned_x(self, text, right_edge, scale):
        # PicoGraphics bitmap font is ~6px wide per character at scale=1.
        text_width = len(text) * 6 * scale
        return max(0, right_edge - text_width)

    def _draw_batting_order(self, x, y, count, current_batter, color_hex, pulse_mix):
        team_pen = self._pen_from_hex(color_hex)
        active_pen = self._pulse_pen(color_hex, pulse_mix)
        for batter in range(count):
            self.g.set_pen(active_pen if batter == current_batter else team_pen)
            self.g.pixel(x + batter * 3, y)

    def _pulse_pen(self, color_hex, pulse_mix):
        step = int(min(max(pulse_mix, 0.0), 1.0) * self._pulse_steps)
        cache_key = (color_hex, step)
        if cache_key in self._pulse_pen_cache:
            return self._pulse_pen_cache[cache_key]
        mix = step / self._pulse_steps
        pulse_color = self._mix_hex_colors(color_hex, "#FFFFFF", mix)
        pen = self._pen_from_hex(pulse_color)
        self._pulse_pen_cache[cache_key] = pen
        return pen

    def _mix_hex_colors(self, color_a, color_b, mix):
        mix = min(max(mix, 0.0), 1.0)
        r_a = int(color_a[1:3], 16)
        g_a = int(color_a[3:5], 16)
        b_a = int(color_a[5:7], 16)
        r_b = int(color_b[1:3], 16)
        g_b = int(color_b[3:5], 16)
        b_b = int(color_b[5:7], 16)
        r = int(r_a + (r_b - r_a) * mix)
        g = int(g_a + (g_b - g_a) * mix)
        b = int(b_a + (b_b - b_a) * mix)
        return "#{:02X}{:02X}{:02X}".format(r, g, b)

    def draw(self):
        s = self.state
        if self._last_brightness != s.brightness:
            self._pen_cache = {}
            self._pulse_pen_cache = {}
            self._last_brightness = s.brightness
        self._apply_brightness()
        pulse_mix = (math.sin(time.ticks_ms() / 200.0) + 1.0) / 2.0
        self.g.set_pen(self.BLACK)
        self.g.clear()

        self.g.set_pen(self._pen_from_hex(s.text_colors["team_a_name"]))
        self.g.text(s.team_a, 0, 0, scale=1)
        if BATTING_ORDER_ENABLED:
            self._draw_batting_order(0, 9, s.batting_order_a, s.current_batter_a, s.text_colors["team_a_name"], pulse_mix)
        self.g.set_pen(self._pen_from_hex(s.text_colors["team_a_score"]))
        score_a_text = str(s.score_a)
        self.g.text(score_a_text, self._right_aligned_x(score_a_text, 64, 2), 8, scale=2)

        self.g.set_pen(self._pen_from_hex(s.text_colors["team_b_name"]))
        self.g.text(s.team_b, 0, 20, scale=1)
        if BATTING_ORDER_ENABLED:
            self._draw_batting_order(0, 29, s.batting_order_b, s.current_batter_b, s.text_colors["team_b_name"], pulse_mix)
        self.g.set_pen(self._pen_from_hex(s.text_colors["team_b_score"]))
        score_b_text = str(s.score_b)
        self.g.text(score_b_text, self._right_aligned_x(score_b_text, 64, 2), 27, scale=2)

        self.g.set_pen(self._pen_from_hex(s.text_colors["inning_label"]))
        self.g.text("INN", 1, 40, scale=1)

        inning_half_text = "TOP" if s.inning_half == "top" else "BOT"
        inning_half_color = s.text_colors["team_a_name"] if s.inning_half == "top" else s.text_colors["team_b_name"]
        self.g.set_pen(self._pen_from_hex(inning_half_color))
        self.g.text(inning_half_text, 1, 47, scale=1)

        inning_text = str(s.inning)
        inning_x = 22
        inning_y = 39
        inning_scale = 2

        self.g.set_pen(self._pen_from_hex(s.text_colors["inning_value"]))
        self.g.text(inning_text, inning_x, inning_y, scale=inning_scale)

        i2c_bus = getattr(self.i75, "i2c", None)
        if i2c_bus is not None:
            temperature_f = self.temperature_reader.get_temperature_f(i2c_bus)
            if temperature_f is not None:
                temp_text = str(temperature_f)
                temp_y = 55
                temp_x = 0
                f_x = temp_x + (len(temp_text) * 6) + 6
                degree_x = f_x - 5
                degree_y = temp_y + 1

                temp_pen = self._pen_from_hex(s.text_colors["count_labels"])
                self.g.set_pen(temp_pen)
                self.g.text(temp_text, temp_x, temp_y, scale=1)
                self.g.pixel(degree_x, degree_y)
                self.g.pixel(degree_x + 1, degree_y)
                self.g.pixel(degree_x, degree_y + 1)
                self.g.pixel(degree_x + 1, degree_y + 1)
                self.g.text("F", f_x, temp_y, scale=1)

        self._draw_count_row(43, "B", s.balls, 3)
        self._draw_count_row(51, "S", s.strikes, 2)
        self._draw_count_row(59, "O", s.outs, 2)

        self.i75.update()


HTML_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
  <title>Interstate 75 W Scoreboard</title>
  <style>
    body {{ font-family: sans-serif; background: #111; color: #eee; margin: 16px; }}
    .card {{ background: #1d1d1d; border: 1px solid #333; border-radius: 8px; padding: 12px; margin-bottom: 12px; }}
    .row {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    button {{ padding: 8px 10px; border-radius: 6px; border: 1px solid #666; background: #2a2a2a; color: #fff; }}
    input {{ padding: 8px; border-radius: 6px; border: 1px solid #666; background: #0d0d0d; color: #fff; width: 130px; }}
  </style>
</head>
<body>
  <h1>Interstate 75 W Baseball Scoreboard</h1>
  <div class=\"card\"><b>{team_a}</b>: {score_a}<br><b>{team_b}</b>: {score_b}<br>Inning: {inning} ({inning_half})<br>Balls: {balls} | Strikes: {strikes} | Outs: {outs}</div>
  {batting_order_controls}

  <div class=\"card\">
    <form method=\"post\" action=\"/rename\">
      <input name=\"team_a\" value=\"{team_a}\"> <input name=\"team_b\" value=\"{team_b}\">
      <button type=\"submit\">Rename</button>
    </form>
  </div>

  <div class=\"card\">
    <form method=\"post\" action=\"/colors\">
      <div class=\"row\">
        <label>Away Team Name <input type=\"color\" name=\"team_a_name\" value=\"{team_a_name_color}\"></label>
        <label>Away Team Score <input type=\"color\" name=\"team_a_score\" value=\"{team_a_score_color}\"></label>
      </div>
      <div class=\"row\">
        <label>Home Team Name <input type=\"color\" name=\"team_b_name\" value=\"{team_b_name_color}\"></label>
        <label>Home Team Score <input type=\"color\" name=\"team_b_score\" value=\"{team_b_score_color}\"></label>
      </div>
      <div class=\"row\">
        <label>Inning Label <input type=\"color\" name=\"inning_label\" value=\"{inning_label_color}\"></label>
        <label>Inning Value <input type=\"color\" name=\"inning_value\" value=\"{inning_value_color}\"></label>
      </div>
      <div class=\"row\">
        <label>Count Labels <input type=\"color\" name=\"count_labels\" value=\"{count_labels_color}\"></label>
        <button type=\"submit\">Save Text Colors</button>
      </div>
    </form>
  </div>

  <div class=\"card\">
    <form method=\"post\" action=\"/brightness\">
      <label>Brightness:
        <input type=\"range\" name=\"brightness\" min=\"0.05\" max=\"1.0\" step=\"0.05\" value=\"{brightness}\" style=\"width: 220px;\">
      </label>
      <span>{brightness_label}</span>
      <button type=\"submit\">Set Brightness</button>
    </form>
  </div>

  <div class=\"card row\">
    <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"score_a_inc\"><button>{team_a} +1</button></form>
    <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"score_a_dec\"><button>{team_a} -1</button></form>
    <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"score_b_inc\"><button>{team_b} +1</button></form>
    <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"score_b_dec\"><button>{team_b} -1</button></form>
  </div>

  <div class=\"card row\">
    <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"inning_inc\"><button>Inning +1</button></form>
    <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"inning_dec\"><button>Inning -1</button></form>
    <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"half_toggle\"><button>Top/Bottom</button></form>
  </div>

  <div class=\"card row\">
    <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"balls_cycle\"><button>Balls</button></form>
    <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"strikes_cycle\"><button>Strikes</button></form>
    <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"outs_cycle\"><button>Outs</button></form>
  </div>

  <div class=\"card\">
    <b>Reset Controls</b>
    <div class=\"row\">
      <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"reset_count\"><button type=\"submit\" onclick=\"return confirm('Reset balls and strikes?');\">Reset Count</button></form>
      <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"reset_scores\"><button type=\"submit\" onclick=\"return confirm('Reset both team scores?');\">Reset Scores</button></form>
      <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"reset\"><button type=\"submit\" onclick=\"return confirm('Reset the full scoreboard?');\">Reset All</button></form>
    </div>
  </div>
</body></html>
"""

BATTING_ORDER_HTML = """<div class=\"card\">
    <b>Batting Order</b><br>
    Away Team Batter: {current_batter_a}/{batting_order_a} | Home Team Batter: {current_batter_b}/{batting_order_b}
    <div class=\"row\" style=\"margin-top: 8px;\">
      <form method=\"post\" action=\"/batting-order\">
        <label>Away Team Batters <input type=\"number\" min=\"1\" max=\"20\" name=\"batting_order_a\" value=\"{batting_order_a}\"></label>
        <label>Home Team Batters <input type=\"number\" min=\"1\" max=\"20\" name=\"batting_order_b\" value=\"{batting_order_b}\"></label>
        <button type=\"submit\">Save Batting Order</button>
      </form>
    </div>
    <div class=\"row\" style=\"margin-top: 8px;\">
      <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"batter_current_advance\"><button>Advance Current Batter</button></form>
      <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"batter_a_advance\"><button>Advance Away Team Batter</button></form>
      <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"batter_b_advance\"><button>Advance Home Team Batter</button></form>
    </div>
  </div>"""


def url_decode(text):
    text = text.replace("+", " ")
    out = ""
    i = 0
    while i < len(text):
        if text[i] == "%" and i + 2 < len(text):
            try:
                out += chr(int(text[i + 1 : i + 3], 16))
                i += 3
                continue
            except ValueError:
                pass
        out += text[i]
        i += 1
    return out


def parse_form(body):
    values = {}
    if not body:
        return values
    for part in body.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            values[url_decode(k)] = url_decode(v)
    return values


async def handle_client(reader, writer, state):
    try:
        request_line = (await reader.readline()).decode("utf-8")
        if not request_line:
            await writer.aclose()
            return

        method, path, _ = request_line.strip().split(" ")

        content_length = 0
        while True:
            header = (await reader.readline()).decode("utf-8")
            if header in ("\r\n", "\n", ""):
                break
            lower = header.lower()
            if lower.startswith("content-length:"):
                content_length = int(lower.split(":", 1)[1].strip())

        body = ""
        if method == "POST" and content_length > 0:
            body = (await reader.read(content_length)).decode("utf-8")

        if method == "POST" and path == "/action":
            values = parse_form(body)
            state.update(values.get("action", ""))
            response = "HTTP/1.1 303 See Other\r\nLocation: /\r\n\r\n"
        elif method == "POST" and path == "/rename":
            values = parse_form(body)
            state.rename(values.get("team_a", "AWAY TEAM"), values.get("team_b", "HOME TEAM"))
            response = "HTTP/1.1 303 See Other\r\nLocation: /\r\n\r\n"
        elif method == "POST" and path == "/colors":
            values = parse_form(body)
            state.update_text_colors(values)
            response = "HTTP/1.1 303 See Other\r\nLocation: /\r\n\r\n"
        elif method == "POST" and path == "/brightness":
            values = parse_form(body)
            state.set_brightness(values.get("brightness", "1.0"))
            response = "HTTP/1.1 303 See Other\r\nLocation: /\r\n\r\n"
        elif method == "POST" and path == "/batting-order":
            values = parse_form(body)
            state.set_batting_order(values.get("batting_order_a", "9"), values.get("batting_order_b", "9"))
            response = "HTTP/1.1 303 See Other\r\nLocation: /\r\n\r\n"
        else:
            batting_order_controls = ""
            if BATTING_ORDER_ENABLED:
                batting_order_controls = BATTING_ORDER_HTML.format(
                    batting_order_a=state.batting_order_a,
                    batting_order_b=state.batting_order_b,
                    current_batter_a=state.current_batter_a + 1,
                    current_batter_b=state.current_batter_b + 1,
                )
            page = HTML_TEMPLATE.format(
                team_a=state.team_a,
                team_b=state.team_b,
                score_a=state.score_a,
                score_b=state.score_b,
                inning=state.inning,
                inning_half=state.inning_half,
                balls=state.balls,
                strikes=state.strikes,
                outs=state.outs,
                team_a_name_color=state.text_colors["team_a_name"],
                team_a_score_color=state.text_colors["team_a_score"],
                team_b_name_color=state.text_colors["team_b_name"],
                team_b_score_color=state.text_colors["team_b_score"],
                inning_label_color=state.text_colors["inning_label"],
                inning_value_color=state.text_colors["inning_value"],
                count_labels_color=state.text_colors["count_labels"],
                brightness=state.brightness,
                brightness_label="{:.0f}%".format(state.brightness * 100),
                batting_order_controls=batting_order_controls,
            )
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/html\r\n"
                "Connection: close\r\n\r\n" + page
            )

        await writer.awrite(response)
    except Exception as exc:
        print("HTTP error:", exc)
    finally:
        await writer.aclose()


def connect_wifi():
    if network is None:
        print("No network module available.")
        return None

    try:
        import secrets

        ssid = secrets.WIFI_SSID
        password = secrets.WIFI_PASSWORD
    except Exception:
        print("Wi-Fi disabled. Create secrets.py with WIFI_SSID/WIFI_PASSWORD to enable web control.")
        return None

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    configured_hostname = False

    # Newer MicroPython builds expose network.hostname("name").
    try:
        network.hostname(DEVICE_HOSTNAME)
        configured_hostname = True
    except Exception:
        pass

    # Older builds may expose hostname only via WLAN config keys.
    if not configured_hostname:
        for key in ("hostname", "dhcp_hostname"):
            try:
                wlan.config(**{key: DEVICE_HOSTNAME})
                configured_hostname = True
                break
            except Exception:
                pass

    if configured_hostname:
        print("Configured DHCP hostname: %s" % DEVICE_HOSTNAME)
    else:
        print("Could not configure DHCP hostname on this firmware.")

    if not wlan.isconnected():
        print("Connecting Wi-Fi...", ssid)
        wlan.connect(ssid, password)
        for _ in range(40):
            if wlan.isconnected():
                break
            time.sleep(0.25)

    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        # Some networks resolve DHCP hostnames (for example http://score),
        # while .local requires mDNS support on both firmware and client.
        mdns_ready = False
        try:
            import mdns

            # Probe without relying on a specific mdns API variant.
            server_obj = None
            if hasattr(mdns, "Server"):
                try:
                    server_obj = mdns.Server()
                except Exception:
                    server_obj = None

            configured = False
            if server_obj and hasattr(server_obj, "hostname"):
                try:
                    server_obj.hostname(DEVICE_HOSTNAME)
                    configured = True
                except Exception:
                    pass
            if not configured and hasattr(mdns, "hostname"):
                try:
                    mdns.hostname(DEVICE_HOSTNAME)
                    configured = True
                except Exception:
                    pass
            mdns_ready = configured
        except Exception:
            mdns_ready = False

        print("Wi-Fi connected, browse to http://%s" % ip)
        print("Try DHCP name: http://%s" % DEVICE_HOSTNAME)
        if mdns_ready:
            print("mDNS active, try: http://%s.local" % DEVICE_HOSTNAME)
        else:
            print(".local name unavailable: mDNS not active on this firmware/client.")
    else:
        print("Wi-Fi connection failed.")
    return wlan


async def render_loop(renderer):
    while True:
        renderer.draw()
        await asyncio.sleep_ms(120)


async def main_async():
    state = ScoreboardState()
    renderer = MatrixRenderer(state)

    connect_wifi()

    await asyncio.start_server(lambda r, w: handle_client(r, w, state), "0.0.0.0", 80)
    print("HTTP server listening on port 80")

    asyncio.create_task(render_loop(renderer))

    while True:
        await asyncio.sleep(1)


try:
    asyncio.run(main_async())
finally:
    asyncio.new_event_loop()
