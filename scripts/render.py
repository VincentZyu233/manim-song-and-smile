"""Render Manim and mux the original MP3 into a portable final MP4."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "lyric_garden.py"
MUSIC = ROOT / "music" / "歌声与微笑.mp3"
TIMELINE = ROOT / "assets" / "lyrics" / "timeline.json"


def run(*command: str, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, env=env)


def newest_video(directory: Path) -> Path:
    videos = list(directory.rglob("LyricGarden.mp4"))
    if not videos:
        raise FileNotFoundError(f"Manim did not create LyricGarden.mp4 in {directory}")
    return max(videos, key=lambda video: video.stat().st_mtime)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quality", choices=("preview", "final"), default="preview")
    parser.add_argument("--duration", type=float, help="Limit a preview to this many seconds.")
    parser.add_argument("--waveform", choices=("bars", "static", "scroll"), default="bars", help="Top visualisation: reacting spectrum bars, static envelope or scrolling envelope.")
    parser.add_argument("--bottom", choices=("static", "none"), default="static", help="Add the whole song envelope above the progress bar.")
    parser.add_argument("--bottom-lift", type=float, default=4.6, help="Lift the bottom envelope, progress bar and clock clear of a phone player's overlay.")
    parser.add_argument("--fps", type=int, default=60, help="Frame rate of the render.")
    parser.add_argument('--path', type=Path, required=True, help='LXGW WenKai TTF file')
    parser.add_argument('--work', type=Path, required=True, help='Temporary render directory')
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.path.is_file():
        parser.error('Font file does not exist: ' + str(args.path))
    from fontTools.ttLib import TTFont
    import manimpango
    try:
        with TTFont(args.path) as face:
            family = face['name'].getDebugName(16) or face['name'].getDebugName(1)
        if not family or not manimpango.register_font(str(args.path.resolve())):
            raise ValueError('font registration failed')
    except Exception as exc:
        parser.error('Cannot load font: ' + str(exc))
    if args.quality == "final" and args.duration:
        parser.error("--duration is only supported for preview renders")
    duration = args.duration if args.duration else None
    media = args.work.resolve() / 'manim' / args.quality
    output = args.output or ROOT / "output" / ("song-and-smile-preview.mp4" if duration else "song-and-smile.mp4")
    output.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ | {'LYRIC_GARDEN_FONT_PATH': str(args.path.resolve()), 'LYRIC_GARDEN_DURATION': str(duration or 0), 'LYRIC_GARDEN_WAVEFORM': args.waveform, 'LYRIC_GARDEN_BOTTOM': args.bottom, 'LYRIC_GARDEN_BOTTOM_LIFT': str(args.bottom_lift), 'LYRIC_GARDEN_FPS': str(args.fps), 'LYRIC_GARDEN_WIDTH': '540' if args.quality == 'preview' else '1080', 'LYRIC_GARDEN_HEIGHT': '960' if args.quality == 'preview' else '1920'}
    if duration:
        env["LYRIC_GARDEN_DURATION"] = str(duration)
    quality_flag = "-ql" if args.quality == "preview" else "-qh"
    run(sys.executable, '-m', 'manim', str(SOURCE), 'LyricGarden', quality_flag, '--media_dir', str(media), '--format', 'mp4', '--progress_bar', 'none', env=env)
    scene = newest_video(media)
    mux_args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(scene), "-i", str(MUSIC), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac"]
    target_duration = duration or json.loads(TIMELINE.read_text(encoding="utf-8"))["duration"]
    mux_args.extend(("-t", str(target_duration)))
    mux_args.append(str(output))
    run(*mux_args)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
