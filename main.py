"""Baseball scoreboard for Pimoroni Interstate 75 W (64x64 HUB75).

Copy this file to your Interstate 75 W as /main.py.
Optionally add /secrets.py with WIFI_SSID and WIFI_PASSWORD to enable
phone/browser control over Wi-Fi.
"""

import uasyncio as asyncio
import time

try:
    import network
except ImportError:
    network = None

from interstate75 import Interstate75, DISPLAY_INTERSTATE75_64X64


class ScoreboardState:
    def __init__(self):
        self.team_a = "TEAM A"
        self.team_b = "TEAM B"
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

    def clamp(self):
        self.score_a = max(0, self.score_a)
        self.score_b = max(0, self.score_b)
        self.inning = max(1, self.inning)
        self.balls = min(max(0, self.balls), 3)
        self.strikes = min(max(0, self.strikes), 2)
        self.outs = min(max(0, self.outs), 2)
        if self.inning_half not in ("top", "bottom"):
            self.inning_half = "top"

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
            self.strikes = (self.strikes + 1) % 3
        elif action == "outs_cycle":
            self.outs = (self.outs + 1) % 3
        elif action == "reset":
            self.score_a = 0
            self.score_b = 0
            self.inning = 1
            self.inning_half = "top"
            self.balls = 0
            self.strikes = 0
            self.outs = 0
        self.clamp()

    def rename(self, team_a, team_b):
        self.team_a = (team_a or "TEAM A").strip().upper()[:10]
        self.team_b = (team_b or "TEAM B").strip().upper()[:10]

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

        self.BLACK = self.g.create_pen(0, 0, 0)
        self.WHITE = self.g.create_pen(255, 255, 255)
        self.RED = self.g.create_pen(255, 40, 0)
        self.DIM = self.g.create_pen(48, 48, 48)
        self._pen_cache = {}

    def _pen_from_hex(self, color_hex):
        if color_hex in self._pen_cache:
            return self._pen_cache[color_hex]
        r = int(color_hex[1:3], 16)
        g = int(color_hex[3:5], 16)
        b = int(color_hex[5:7], 16)
        pen = self.g.create_pen(r, g, b)
        self._pen_cache[color_hex] = pen
        return pen

    def _draw_count_row(self, y, label, count, max_count):
        s = self.state
        self.g.set_pen(self._pen_from_hex(s.text_colors["count_labels"]))
        self.g.text(label, 36, y - 3, scale=1)
        for i in range(max_count):
            self.g.set_pen(self.RED if i < count else self.DIM)
            self.g.circle(45 + i * 7, y, 2)

    def draw(self):
        s = self.state
        self.g.set_pen(self.BLACK)
        self.g.clear()

        self.g.set_pen(self._pen_from_hex(s.text_colors["team_a_name"]))
        self.g.text(s.team_a, 1, 1, scale=1)
        self.g.set_pen(self._pen_from_hex(s.text_colors["team_a_score"]))
        self.g.text(str(s.score_a), 52, 1, scale=2)

        self.g.set_pen(self._pen_from_hex(s.text_colors["team_b_name"]))
        self.g.text(s.team_b, 1, 17, scale=1)
        self.g.set_pen(self._pen_from_hex(s.text_colors["team_b_score"]))
        self.g.text(str(s.score_b), 52, 17, scale=2)

        self.g.set_pen(self._pen_from_hex(s.text_colors["inning_label"]))
        self.g.text("INN", 1, 45, scale=1)
        self.g.set_pen(self._pen_from_hex(s.text_colors["inning_value"]))
        self.g.text(str(s.inning), 22, 43, scale=2)

        self.g.set_pen(self.RED)
        if s.inning_half == "top":
            self.g.triangle(30, 33, 24, 39, 36, 39)
        else:
            self.g.triangle(24, 57, 36, 57, 30, 63)

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

  <div class=\"card\">
    <form method=\"post\" action=\"/rename\">
      <input name=\"team_a\" maxlength=\"10\" value=\"{team_a}\"> <input name=\"team_b\" maxlength=\"10\" value=\"{team_b}\">
      <button type=\"submit\">Rename</button>
    </form>
  </div>

  <div class=\"card\">
    <form method=\"post\" action=\"/colors\">
      <div class=\"row\">
        <label>Team A Name <input type=\"color\" name=\"team_a_name\" value=\"{team_a_name_color}\"></label>
        <label>Team A Score <input type=\"color\" name=\"team_a_score\" value=\"{team_a_score_color}\"></label>
      </div>
      <div class=\"row\">
        <label>Team B Name <input type=\"color\" name=\"team_b_name\" value=\"{team_b_name_color}\"></label>
        <label>Team B Score <input type=\"color\" name=\"team_b_score\" value=\"{team_b_score_color}\"></label>
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

  <div class=\"card row\">
    <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"score_a_inc\"><button>Team A +1</button></form>
    <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"score_a_dec\"><button>Team A -1</button></form>
    <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"score_b_inc\"><button>Team B +1</button></form>
    <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"score_b_dec\"><button>Team B -1</button></form>
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
    <form method=\"post\" action=\"/action\"><input type=\"hidden\" name=\"action\" value=\"reset\"><button>Reset</button></form>
  </div>
</body></html>
"""


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
            state.rename(values.get("team_a", "TEAM A"), values.get("team_b", "TEAM B"))
            response = "HTTP/1.1 303 See Other\r\nLocation: /\r\n\r\n"
        elif method == "POST" and path == "/colors":
            values = parse_form(body)
            state.update_text_colors(values)
            response = "HTTP/1.1 303 See Other\r\nLocation: /\r\n\r\n"
        else:
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

    # Try to make the board discoverable as http://score.local on networks
    # that support local hostname resolution (mDNS/router DNS).
    for key in ("hostname", "dhcp_hostname"):
        try:
            wlan.config(**{key: "score"})
            print("Configured network hostname: score.local")
            break
        except Exception:
            pass

    if not wlan.isconnected():
        print("Connecting Wi-Fi...", ssid)
        wlan.connect(ssid, password)
        for _ in range(40):
            if wlan.isconnected():
                break
            time.sleep(0.25)

    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print("Wi-Fi connected, browse to http://%s" % ip)
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
