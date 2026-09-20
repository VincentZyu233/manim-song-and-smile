"""Convert the supplied LRC file into the timeline consumed by Manim."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LRC = ROOT / "music" / "qq音乐拿到的歌词.txt"
DEFAULT_AUDIO = ROOT / "music" / "歌声与微笑.mp3"
DEFAULT_OUTPUT = ROOT / "assets" / "lyrics" / "timeline.json"
STAMP = re.compile(r"\[(?P<minutes>\d{2}):(?P<seconds>\d{2}\.\d{2})\]")
META = re.compile(r"\[(?P<key>[a-z]+):(?P<value>.*)\]", re.IGNORECASE)
KEYWORDS = (
    ("海角天涯", "horizon"),
    ("遍野春花", "spring_flower"),
    ("春花", "spring_flower"),
    ("微笑", "smile"),
    ("留下", "keep"),
    ("歌声", "song"),
    ("家", "home"),
)


def seconds(match: re.Match[str]) -> float:
    return int(match["minutes"]) * 60 + float(match["seconds"])


def audio_duration(audio: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(audio)],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def classify(text: str) -> tuple[str, str]:
    for suffix, kind in KEYWORDS:
        if text.endswith(suffix):
            return text[: -len(suffix)], kind
    return text, "neutral"


def parse_lrc(path: Path) -> tuple[dict[str, str], list[tuple[float, str]]]:
    metadata: dict[str, str] = {}
    events: list[tuple[float, str]] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        raw = raw.strip()
        meta = META.fullmatch(raw)
        if meta:
            metadata[meta["key"].lower()] = meta["value"].strip()
            continue
        marks = list(STAMP.finditer(raw))
        if not marks:
            continue
        text = STAMP.sub("", raw).strip()
        events.extend((seconds(mark), text) for mark in marks)
    return metadata, sorted(events, key=lambda event: event[0])


def build_timeline(lrc: Path, audio: Path) -> dict:
    metadata, events = parse_lrc(lrc)
    lyric_events = [event for event in events if event[1] and not event[1].startswith(("歌声与微笑 -", "词：", "曲："))]
    cues = []
    for index, (start, text) in enumerate(lyric_events):
        following = [time for time, _ in events if time > start]
        end = following[0] if following else min(audio_duration(audio), start + 2.6)
        prefix, kind = classify(text)
        keyword = text[len(prefix):]
        keyword_start = start + max(0.55, (end - start) * (len(prefix) / max(len(text), 1)))
        cues.append({
            "id": f"line_{index + 1:02d}",
            "text": text,
            "start": round(start, 3),
            "end": round(end, 3),
            "prefix": prefix,
            "keyword": keyword,
            "keyword_kind": kind,
            "keyword_start": round(min(keyword_start, end - 0.18), 3),
            "reviewed": False,
        })
    return {
        "version": 1,
        "audio": str(audio.relative_to(ROOT)).replace("\\", "/"),
        "duration": round(audio_duration(audio), 3),
        "metadata": {"title": metadata.get("ti", "歌声与微笑"), "artist": metadata.get("ar", "新月合唱团"), "lyricist": "王健", "composer": "谷建芬"},
        "intro_end": cues[0]["start"],
        "outro_start": cues[-1]["end"],
        "cues": cues,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lrc", type=Path, default=DEFAULT_LRC)
    parser.add_argument("--audio", type=Path, default=DEFAULT_AUDIO)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    timeline = build_timeline(args.lrc, args.audio)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(timeline['cues'])} lyric cues to {args.output}")


if __name__ == "__main__":
    main()
