#!/usr/bin/env python3
from __future__ import annotations

import argparse
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from flask import Flask, redirect, render_template, request, url_for
from PIL import Image, ImageDraw, ImageFont

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
except ImportError:  # Non-Pi/dev environment fallback
    RGBMatrix = None
    RGBMatrixOptions = None


@dataclass
class ScoreboardState:
    team_a: str = "TEAM A"
    team_b: str = "TEAM B"
    score_a: int = 0
    score_b: int = 0
    inning: int = 1
    inning_half: str = "top"  # top|bottom
    balls: int = 0  # 0..3
    strikes: int = 0  # 0..2
    outs: int = 0  # 0..2
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def clamp(self) -> None:
        self.score_a = max(0, self.score_a)
        self.score_b = max(0, self.score_b)
        self.inning = max(1, self.inning)
        self.balls = min(max(0, self.balls), 3)
        self.strikes = min(max(0, self.strikes), 2)
        self.outs = min(max(0, self.outs), 2)
        if self.inning_half not in {"top", "bottom"}:
            self.inning_half = "top"

    def update(self, action: str) -> None:
        with self.lock:
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

    def rename(self, team_a: str, team_b: str) -> None:
        with self.lock:
            self.team_a = (team_a or "TEAM A").strip()[:10].upper()
            self.team_b = (team_b or "TEAM B").strip()[:10].upper()

    def snapshot(self) -> dict:
        with self.lock:
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
            }


class MatrixRenderer:
    def __init__(self, state: ScoreboardState) -> None:
        self.state = state
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.matrix = self._init_matrix()
        self.font_small = ImageFont.load_default()
        self.font_med = ImageFont.load_default()
        self.font_big = ImageFont.load_default()

    def _init_matrix(self):
        if RGBMatrix is None:
            print("rgbmatrix not available - running web UI only.")
            return None

        options = RGBMatrixOptions()
        options.rows = 64
        options.cols = 64
        options.chain_length = 1
        options.parallel = 1
        options.hardware_mapping = "adafruit-hat"
        options.brightness = 60
        options.gpio_slowdown = 4
        options.pwm_bits = 11
        # Many 64x64 HUB75 panels need explicit row addressing to avoid
        # quarter-band output (e.g. only 1st/3rd vertical quarters lit).
        # We set these conservatively and only when available in the local
        # rgbmatrix build so this remains compatible across versions.
        self._set_option_if_supported(options, "row_address_type", 5)
        self._set_option_if_supported(options, "multiplexing", 0)
        self._set_option_if_supported(options, "disable_hardware_pulsing", True)
        self._set_option_if_supported(options, "limit_refresh_rate_hz", 120)
        return RGBMatrix(options=options)

    @staticmethod
    def _set_option_if_supported(options, name: str, value) -> None:
        if hasattr(options, name):
            setattr(options, name, value)

    def start(self) -> None:
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def _run(self) -> None:
        while self.running:
            frame = self._render_frame()
            if self.matrix:
                self.matrix.SetImage(frame.convert("RGB"))
            time.sleep(0.1)

    def _fit_text(self, draw: ImageDraw.ImageDraw, text: str, max_width: int, base_size: int) -> ImageFont.ImageFont:
        size = base_size
        while size >= 8:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
            except OSError:
                font = ImageFont.load_default()
            width = draw.textlength(text, font=font)
            if width <= max_width:
                return font
            size -= 1
        return ImageFont.load_default()

    def _draw_circles(self, draw: ImageDraw.ImageDraw, x: int, y: int, on_count: int, max_count: int = 3) -> None:
        r = 4
        gap = 3
        for i in range(max_count):
            cx = x + i * (2 * r + gap)
            fill = (255, 40, 0) if i < on_count else (55, 55, 55)
            draw.ellipse((cx, y, cx + 2 * r, y + 2 * r), fill=fill)

    def _render_frame(self) -> Image.Image:
        s = self.state.snapshot()

        img = Image.new("RGB", (64, 64), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Team lines
        team_font = self._fit_text(draw, s["team_a"], 38, 13)
        score_font = self._fit_text(draw, str(s["score_a"]), 20, 22)
        draw.text((1, 1), s["team_a"], font=team_font, fill=(255, 255, 255))
        draw.text((50, 0), str(s["score_a"]), font=score_font, fill=(255, 255, 255))

        team_font_b = self._fit_text(draw, s["team_b"], 38, 13)
        score_font_b = self._fit_text(draw, str(s["score_b"]), 20, 22)
        draw.text((1, 17), s["team_b"], font=team_font_b, fill=(255, 255, 255))
        draw.text((50, 16), str(s["score_b"]), font=score_font_b, fill=(255, 255, 255))

        # Inning block
        draw.text((1, 46), "INN", font=ImageFont.load_default(), fill=(255, 255, 255))
        inn_font = self._fit_text(draw, str(s["inning"]), 16, 20)
        draw.text((20, 45), str(s["inning"]), font=inn_font, fill=(255, 255, 255))

        if s["inning_half"] == "top":
            draw.polygon([(24, 39), (30, 33), (36, 39)], fill=(255, 35, 0))
        else:
            draw.polygon([(24, 63), (30, 57), (36, 63)], fill=(255, 35, 0))

        # B/S/O
        draw.text((39, 43), "B", font=ImageFont.load_default(), fill=(255, 255, 255))
        draw.text((39, 51), "S", font=ImageFont.load_default(), fill=(255, 255, 255))
        draw.text((39, 59), "O", font=ImageFont.load_default(), fill=(255, 255, 255))
        self._draw_circles(draw, 47, 43, s["balls"], max_count=3)
        self._draw_circles(draw, 47, 51, s["strikes"], max_count=2)
        self._draw_circles(draw, 47, 59, s["outs"], max_count=2)

        return img


def create_app(state: ScoreboardState) -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("index.html", state=state.snapshot())

    @app.post("/action")
    def action():
        state.update(request.form["action"])
        return redirect(url_for("index"))

    @app.post("/rename")
    def rename():
        state.rename(request.form.get("team_a", ""), request.form.get("team_b", ""))
        return redirect(url_for("index"))

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="64x64 baseball scoreboard")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    state = ScoreboardState()
    renderer = MatrixRenderer(state)
    renderer.start()

    app = create_app(state)
    app.run(host=args.host, port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
