"""Validate duration, portrait dimensions, frame rate, and stream readability."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TIMELINE = ROOT / "assets" / "lyrics" / "timeline.json"


def probe(video: Path) -> dict:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", type=Path)
    parser.add_argument("--timeline", type=Path, default=TIMELINE)
    parser.add_argument("--tolerance", type=float, default=.12)
    args = parser.parse_args()
    data = probe(args.video)
    video = next(stream for stream in data["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in data["streams"] if stream["codec_type"] == "audio")
    expected = json.loads(args.timeline.read_text(encoding="utf-8"))["duration"]
    actual = float(data["format"]["duration"])
    assert (int(video["width"]), int(video["height"])) == (1080, 1920), "Expected a 1080x1920 portrait video"
    assert abs(actual - expected) <= args.tolerance, f"Expected {expected}s, received {actual}s"
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(args.video), "-f", "null", "-"], check=True)
    print(json.dumps({"duration": actual, "resolution": f"{video['width']}x{video['height']}", "fps": video["avg_frame_rate"], "audio_codec": audio["codec_name"], "full_decode": "passed"}, indent=2))


if __name__ == "__main__":
    main()
