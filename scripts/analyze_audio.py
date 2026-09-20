"""Extract lightweight, dependency-free loudness data for animation review."""

from __future__ import annotations

import argparse
import array
import json
import math
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIO = ROOT / "music" / "歌声与微笑.mp3"
DEFAULT_OUTPUT = ROOT / "build" / "audio-analysis.json"


def pcm_samples(audio: Path, sample_rate: int) -> array.array:
    process = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(audio), "-ac", "1", "-ar", str(sample_rate), "-f", "s16le", "-"],
        check=True,
        capture_output=True,
    )
    samples = array.array("h")
    samples.frombytes(process.stdout)
    return samples


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", type=Path, default=DEFAULT_AUDIO)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sample-rate", type=int, default=8_000)
    parser.add_argument("--window", type=float, default=0.05)
    args = parser.parse_args()

    samples = pcm_samples(args.audio, args.sample_rate)
    width = max(1, round(args.window * args.sample_rate))
    points = []
    for start in range(0, len(samples), width):
        chunk = samples[start:start + width]
        if not chunk:
            continue
        rms = math.sqrt(sum(sample * sample for sample in chunk) / len(chunk)) / 32768
        peak = max(abs(sample) for sample in chunk) / 32768
        points.append({"time": round(start / args.sample_rate, 3), "rms": round(rms, 5), "peak": round(peak, 5)})
    payload = {"sample_rate": args.sample_rate, "window": args.window, "points": points}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(points)} waveform windows to {args.output}")


if __name__ == "__main__":
    main()

