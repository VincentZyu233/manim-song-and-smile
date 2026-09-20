"""Portrait lyrics in LXGW WenKai with semantic ending-word colors."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import numpy as np
from manim import ArcBetweenPoints, Create, Dot, DOWN, FadeOut, Line, Rectangle, Scene, Text, UP, VMobject, VGroup, Write, config


ROOT = Path(__file__).resolve().parents[1]
TIMELINE_PATH = ROOT / "assets" / "lyrics" / "timeline.json"
import manimpango
from fontTools.ttLib import TTFont
FONT_PATH = Path(os.environ['LYRIC_GARDEN_FONT_PATH'])
with TTFont(FONT_PATH) as face:
    FONT = face['name'].getDebugName(16) or face['name'].getDebugName(1)
if not FONT or not manimpango.register_font(str(FONT_PATH)):
    raise RuntimeError('Cannot register supplied LXGW font')
MAX_TIME = float(os.environ.get("LYRIC_GARDEN_DURATION", "0"))

config.pixel_width = int(os.environ.get('LYRIC_GARDEN_WIDTH', '1080'))
config.pixel_height = int(os.environ.get('LYRIC_GARDEN_HEIGHT', '1920'))
config.frame_width = 9
config.frame_height = 16
config.frame_rate = int(os.environ.get('LYRIC_GARDEN_FPS', '30'))
config.background_color = "#0D1520"

PALETTE = {
    "neutral": "#F6F0E5", "home": "#F3C66A", "keep": "#EE786B",
    "smile": "#EE786B", "song": "#72C8D4", "horizon": "#72C8D4",
    "spring_flower": "#75C98D",
}

# Animation-only pre-roll. The timeline stays the single source of truth: these
# offsets move when a phrase starts drawing, never when the next cue may start.
FADE_OUT = .24          # fade of the outgoing phrase, completes before the next head
LEAD_IN = .30           # a phrase starts drawing this long before its cue start
KEYWORD_LEAD = 1.0      # the colored ending word starts drawing this early
KEYWORD_TAIL = .85      # ...and still finishes this long after its keyword_start
KEYWORD_RUN_MIN = .55   # never draw the colored word faster than this
OUTRO_FADE = 3.0        # fade of the closing title and smile arc, ends on the last frame

# Heads-up display: reacting spectrum bars or the envelope waveform on top, the
# progress bar with the elapsed clock at the bottom. Geometry is in frame units.
WAVEFORM_MODE = os.environ.get("LYRIC_GARDEN_WAVEFORM", "bars")
if WAVEFORM_MODE not in ("bars", "static", "scroll"):
    raise RuntimeError(f"Unknown LYRIC_GARDEN_WAVEFORM {WAVEFORM_MODE}")
WAVEFORM_PATH = ROOT / "assets" / "audio" / "waveform.json"
SPECTRUM_PATH = ROOT / "assets" / "audio" / "spectrum.json"
HUD_WIDTH = 7.75
HUD_TOP = 6.55          # centre of the top visualisation
HUD_TOP_HEIGHT = 1.25   # tallest bucket at full scale
HUD_BOTTOM = -6.95      # centre of the progress bar
HUD_BAR_HEIGHT = .09
BOTTOM_WAVE = -6.15     # centre of the whole song envelope below the top visualisation
BOTTOM_WAVE_HEIGHT = .9
BUCKET_FALL = 1.4       # per second fall back of a spectrum bucket
BUCKET_MIN_HEIGHT = .02  # never collapse a bucket: a zero height breaks the next rescale
BUCKET_PEAK_FALL = .22  # per second fall of the peak-hold cap, so the caps keep drifting
BUCKET_CAP_HEIGHT = .07
BOTTOM_MODE = os.environ.get("LYRIC_GARDEN_BOTTOM", "static")
if BOTTOM_MODE not in ("static", "none"):
    raise RuntimeError(f"Unknown LYRIC_GARDEN_BOTTOM {BOTTOM_MODE}")


def load_asset(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError(f"Missing {path}, run scripts/extract_audio.py first")
    return json.loads(path.read_text(encoding="utf-8"))




class LyricGarden(Scene):
    def setup(self) -> None:
        # The head-up display is added as one VGroup, so its updaters sit on
        # descendants and Manim's static-wait optimisation cannot see them. This
        # must be set on the instance: Scene.__init__ assigns its own default.
        self.always_update_mobjects = True
        self.timeline = json.loads(TIMELINE_PATH.read_text(encoding="utf-8"))
        self.limit = min(self.timeline["duration"], MAX_TIME) if MAX_TIME else self.timeline["duration"]
        self.clock = 0.0
        self.hud_stamp = ""
        self.active_lyric: VGroup | None = None
        self.camera.background_color = "#0D1520"

    def wait_until(self, target: float) -> None:
        target = round(min(target, self.limit) * config.frame_rate) / config.frame_rate
        if target > self.clock:
            frames = round((target - self.clock) * config.frame_rate)
            if frames > 0:
                self.wait(frames / config.frame_rate)
            self.clock = self.time

    def play_timed(self, *animations, run_time: float) -> None:
        frames = round(min(run_time, self.limit - self.clock) * config.frame_rate)
        if frames <= 0:
            return
        self.play(*animations, run_time=frames / config.frame_rate)
        self.clock = self.time


    def elapsed(self) -> float:
        return min(max(self.time, 0.0), self.limit)

    def stamp(self, seconds: float) -> str:
        def clock(value: float) -> str:
            return f"{int(value) // 60}:{value % 60:04.1f}"
        return f"{clock(seconds)} / {clock(self.limit)}"

    def waveform_columns(self, asset: dict, start: float, end: float, columns: int) -> tuple[list[float], list[float]]:
        rate = asset["rate"]
        first = max(0, int(start * rate))
        last = min(len(asset["max"]), max(first + 1, int(end * rate)))
        span = max(1.0, (last - first) / columns)
        low, high = [], []
        for index in range(columns):
            head = min(last - 1, first + int(index * span))
            tail = min(last, max(head + 1, first + int((index + 1) * span)))
            low.append(min(asset["min"][head:tail]))
            high.append(max(asset["max"][head:tail]))
        return low, high

    def spectrum_buckets(self) -> VGroup:
        asset = load_asset(SPECTRUM_PATH)
        bands = asset["bands"]
        levels = np.frombuffer(base64.b64decode(asset["data"]), dtype=np.uint8).reshape(-1, bands) / 255
        step = HUD_WIDTH / bands
        centres = [-HUD_WIDTH / 2 + (index + .5) * step for index in range(bands)]
        floor = HUD_TOP - HUD_TOP_HEIGHT / 2
        heights = np.full(bands, .02)
        buckets = VGroup(*[Rectangle(width=step * .62, height=.02, stroke_width=0, fill_opacity=1) for _ in range(bands)])
        buckets.set_color_by_gradient(PALETTE["song"], PALETTE["home"])
        caps = VGroup(*[Rectangle(width=step * .62, height=BUCKET_CAP_HEIGHT, stroke_width=0, fill_color=PALETTE["neutral"], fill_opacity=.7) for _ in range(bands)])
        peaks = np.full(bands, .02)
        def bounce(_: VGroup) -> None:
            row = min(int(self.elapsed() * asset["rate"]), len(levels) - 1)
            heights[:] = np.maximum(levels[row] * HUD_TOP_HEIGHT, heights - BUCKET_FALL / config.frame_rate)
            np.maximum(heights, BUCKET_MIN_HEIGHT, out=heights)
            for bucket, centre, height in zip(buckets, centres, heights):
                bucket.stretch_to_fit_height(float(height))
                bucket.move_to([centre, floor + float(height) / 2, 0])
        buckets.add_updater(bounce)
        def trail(_: VGroup) -> None:
            peaks[:] = np.maximum(heights, peaks - BUCKET_PEAK_FALL / config.frame_rate)
            for cap, centre, peak in zip(caps, centres, peaks):
                cap.move_to([centre, floor + float(peak), 0])
        caps.add_updater(trail)
        return VGroup(buckets, caps)

    def static_waveform(self, columns: int = 240, centre: float = HUD_TOP, height: float = HUD_TOP_HEIGHT) -> VGroup:
        asset = load_asset(WAVEFORM_PATH)
        low, high = self.waveform_columns(asset, 0.0, self.limit, columns)
        scale = height / 2 / max(asset["peak"], 1e-6)
        step = HUD_WIDTH / columns
        def envelope(first: int, last: int, color: str, opacity: float) -> VMobject:
            """One filled band instead of one mobject per column, to keep renders fast."""
            top = [[-HUD_WIDTH / 2 + (index + .5) * step, centre + high[index] * scale, 0] for index in range(first, last)]
            bottom = [[-HUD_WIDTH / 2 + (index + .5) * step, centre + low[index] * scale, 0] for index in reversed(range(first, last))]
            shape = VMobject(stroke_width=0, fill_color=color, fill_opacity=opacity)
            return shape.set_points_as_corners(top + bottom + [top[0]])
        full = envelope(0, columns, "#2A3B4D", .8)
        played = VMobject()
        state = {"reached": 0}
        def reveal(_: VGroup) -> None:
            reached = min(columns, int(self.elapsed() / max(self.limit, 1e-6) * columns))
            if reached > 1 and reached != state["reached"]:
                state["reached"] = reached
                played.become(envelope(0, reached, PALETTE["song"], .8))
        played.add_updater(reveal)
        return VGroup(full, played, self.playhead(centre, height), self.level_dot(asset, centre, height))

    def level_dot(self, asset: dict, centre: float, height: float) -> Dot:
        """Amber dot riding the real envelope at the playhead, so the band is never still."""
        scale = height / 2 / max(asset["peak"], 1e-6)
        dot = Dot(radius=.08, color=PALETTE["home"])
        def ride(mobject: Dot) -> None:
            now = self.elapsed()
            row = min(len(asset["max"]) - 1, max(0, int(now * asset["rate"])))
            level = (asset["max"][row] + asset["min"][row]) / 2 * scale
            mobject.move_to([-HUD_WIDTH / 2 + HUD_WIDTH * min(now / max(self.limit, 1e-6), 1), centre + level, 0])
        dot.add_updater(ride)
        return dot

    def scroll_waveform(self, columns: int = 312, span: float = 5.2) -> VGroup:
        asset = load_asset(WAVEFORM_PATH)
        scale = HUD_TOP_HEIGHT / 2 / max(asset["peak"], 1e-6)
        step = HUD_WIDTH / columns
        band = VMobject()
        def slide(mobject: VMobject) -> None:
            now = self.elapsed()
            low, high = self.waveform_columns(asset, now - span / 2, now + span / 2, columns)
            top = [[-HUD_WIDTH / 2 + (index + .5) * step, HUD_TOP + high[index] * scale, 0] for index in range(columns)]
            bottom = [[-HUD_WIDTH / 2 + (index + .5) * step, HUD_TOP + low[index] * scale, 0] for index in reversed(range(columns))]
            shape = VMobject(stroke_width=1.4, stroke_color=PALETTE["song"], fill_color=PALETTE["song"], fill_opacity=.35)
            mobject.become(shape.set_points_as_corners(top + bottom + [top[0]]))
        band.add_updater(slide)
        marker = Line([0, HUD_TOP - HUD_TOP_HEIGHT / 2 - .08, 0], [0, HUD_TOP + HUD_TOP_HEIGHT / 2 + .08, 0], stroke_width=2, color=PALETTE["home"])
        return VGroup(band, marker)

    def playhead(self, centre: float = HUD_TOP, height: float = HUD_TOP_HEIGHT) -> Line:
        head = Line([0, centre - height / 2 - .08, 0], [0, centre + height / 2 + .08, 0], stroke_width=2, color=PALETTE["home"])
        def track(mobject: Line) -> None:
            mobject.set_x(-HUD_WIDTH / 2 + HUD_WIDTH * min(self.elapsed() / max(self.limit, 1e-6), 1))
        head.add_updater(track)
        return head

    def clock_group(self, sprites: dict[str, Text], text: str) -> VGroup:
        """Assemble the clock from pre-rendered glyph sprites instead of new Text objects."""
        elapsed, total = text.split(" / ")
        def pieces(value: str) -> VGroup:
            return VGroup(*[sprites[character].copy() for character in value]).arrange(buff=.04)
        return VGroup(pieces(elapsed), sprites[" / "].copy(), pieces(total)).arrange(buff=.12)

    def progress_bar(self) -> VGroup:
        track = Rectangle(width=HUD_WIDTH, height=HUD_BAR_HEIGHT, stroke_width=0, fill_color="#223242", fill_opacity=1).move_to([0, HUD_BOTTOM, 0])
        fill = Rectangle(width=.02, height=HUD_BAR_HEIGHT, stroke_width=0, fill_color=PALETTE["home"], fill_opacity=1).move_to([-HUD_WIDTH / 2 + .01, HUD_BOTTOM, 0])
        head = Dot(radius=.075, color=PALETTE["home"]).move_to([-HUD_WIDTH / 2, HUD_BOTTOM, 0])
        def grow(_: Rectangle) -> None:
            width = max(.02, HUD_WIDTH * min(self.elapsed() / max(self.limit, 1e-6), 1))
            fill.stretch_to_fit_width(width)
            fill.move_to([-HUD_WIDTH / 2 + width / 2, HUD_BOTTOM, 0])
            head.move_to([-HUD_WIDTH / 2 + width, HUD_BOTTOM, 0])
        fill.add_updater(grow)
        sprites = {character: Text(character, font=FONT, font_size=26, color="#9CAEBB") for character in "0123456789:."}
        sprites[" / "] = Text(" / ", font=FONT, font_size=26, color="#9CAEBB")
        clock = self.clock_group(sprites, self.stamp(0.0)).move_to([0, HUD_BOTTOM - .40, 0])
        def tick(mobject: VGroup) -> None:
            stamp = self.stamp(self.elapsed())
            if stamp != self.hud_stamp:
                self.hud_stamp = stamp
                mobject.become(self.clock_group(sprites, stamp).move_to(mobject.get_center()))
        clock.add_updater(tick)
        return VGroup(track, fill, head, clock)

    def hud(self) -> VGroup:
        top = {"bars": self.spectrum_buckets, "static": self.static_waveform, "scroll": self.scroll_waveform}[WAVEFORM_MODE]()
        bottom = self.static_waveform(640, BOTTOM_WAVE, BOTTOM_WAVE_HEIGHT) if BOTTOM_MODE == "static" else VGroup()
        return VGroup(top, bottom, self.progress_bar())


    def lyric_mobject(self, cue: dict) -> tuple[VGroup, Text, Text | None]:
        prefix = Text(cue["prefix"], font=FONT, font_size=50, color=PALETTE["neutral"])
        keyword = Text(cue["keyword"], font=FONT, font_size=52, color=PALETTE[cue["keyword_kind"]]) if cue["keyword"] else None
        group = VGroup(prefix, *([keyword] if keyword else [])).arrange(buff=0.06)
        group.scale_to_fit_width(7.75).move_to([0, 1.38, 0])
        return group, prefix, keyword

    def title_sequence(self) -> None:
        title = Text(self.timeline["metadata"]["title"], font=FONT, font_size=64, color=PALETTE["neutral"]).move_to([0, .4, 0])
        artist = Text(self.timeline["metadata"]["artist"], font=FONT, font_size=30, color="#9CAEBB").next_to(title, DOWN, buff=.26)
        credit = Text(f"词：{self.timeline['metadata']['lyricist']}   曲：{self.timeline['metadata']['composer']}", font=FONT, font_size=27, color="#9CAEBB").next_to(artist, DOWN, buff=.18)
        self.wait_until(2.2)
        self.play_timed(Write(title), Write(artist), Write(credit), run_time=2.0)
        self.wait_until(max(5.2, self.timeline["intro_end"] - 1.15))
        self.play_timed(FadeOut(VGroup(title, artist, credit), shift=UP * .2), run_time=.7)

    def present_cue(self, cue: dict, index: int) -> None:
        head_start = cue["start"] - LEAD_IN
        if self.active_lyric:
            self.wait_until(head_start - FADE_OUT)
            self.play_timed(FadeOut(self.active_lyric, shift=UP * .12), run_time=FADE_OUT)
        self.wait_until(head_start)
        group, prefix, keyword = self.lyric_mobject(cue)
        keyword_write_start = cue["keyword_start"] - KEYWORD_LEAD
        prefix_duration = max(.28, min(.9, max(keyword_write_start, head_start) - self.clock))
        self.play_timed(Write(prefix), run_time=prefix_duration)
        if keyword:
            self.wait_until(keyword_write_start)
            keyword_write_end = min(cue["keyword_start"] + KEYWORD_TAIL, cue["end"])
            keyword_duration = max(KEYWORD_RUN_MIN, keyword_write_end - self.clock)
            self.play_timed(Write(keyword), run_time=keyword_duration)
        self.active_lyric = group

    def finale(self) -> None:
        self.wait_until(self.timeline["outro_start"])
        if self.active_lyric:
            self.play_timed(FadeOut(self.active_lyric), run_time=.45)
        smile = ArcBetweenPoints([-2.65, .85, 0], [2.65, .85, 0], angle=1.2, color=PALETTE["keep"], stroke_width=7)
        title = Text(self.timeline["metadata"]["title"], font=FONT, font_size=60, color=PALETTE["neutral"]).move_to([0, 2.05, 0])
        self.play_timed(Create(smile), run_time=1.5)
        self.play_timed(Write(title), run_time=1.2)
        self.wait_until(self.limit - OUTRO_FADE)
        self.play_timed(FadeOut(VGroup(smile, title), shift=DOWN * .18), run_time=max(.4, self.limit - self.clock))
        self.wait_until(self.limit)

    def construct(self) -> None:
        self.add(self.hud())
        self.title_sequence()
        for index, cue in enumerate(self.timeline["cues"]):
            if cue["start"] >= self.limit:
                break
            self.present_cue(cue, index)
        self.finale()
