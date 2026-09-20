"""Portrait lyrics in LXGW WenKai with semantic ending-word colors."""

from __future__ import annotations

import json
import os
from pathlib import Path

from manim import ArcBetweenPoints, Create, DOWN, FadeOut, Scene, Text, UP, VGroup, Write, config


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
config.frame_rate = 30
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




class LyricGarden(Scene):
    def setup(self) -> None:
        self.timeline = json.loads(TIMELINE_PATH.read_text(encoding="utf-8"))
        self.limit = min(self.timeline["duration"], MAX_TIME) if MAX_TIME else self.timeline["duration"]
        self.clock = 0.0
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
        self.wait_until(self.limit)

    def construct(self) -> None:
        self.title_sequence()
        for index, cue in enumerate(self.timeline["cues"]):
            if cue["start"] >= self.limit:
                break
            self.present_cue(cue, index)
        self.finale()
