"""Extract the real waveform and spectrum data used by the lyric scene.

The scene draws its top visualisation from these files, so the picture follows the
actual recording: a min/max envelope for the static and scrolling styles, and a
per-frame frequency spectrum for the reacting bars. Decoding goes through FFmpeg;
the FFT uses numpy, which the scene already gets through Manim.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIO = ROOT / "music" / "歌声与微笑.mp3"
DEFAULT_OUTPUT = ROOT / "assets" / "audio"
SPECTRUM_FLOOR_DB = -42.0


def decode(audio: Path, sample_rate: int) -> np.ndarray:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(audio), "-ac", "1", "-ar", str(sample_rate), "-f", "s16le", "-"],
        check=True,
        capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def envelope(samples: np.ndarray, sample_rate: int, rate: float) -> tuple[np.ndarray, np.ndarray]:
    width = max(1, round(sample_rate / rate))
    frames = len(samples) // width
    trimmed = samples[: frames * width].reshape(frames, width)
    return trimmed.min(axis=1), trimmed.max(axis=1)


def spectrum(samples: np.ndarray, sample_rate: int, rate: float, bands: int, window: int) -> tuple[np.ndarray, np.ndarray]:
    hop = sample_rate / rate
    starts = np.arange(0, max(1, len(samples) - window), int(round(hop)))
    frames = samples[starts[:, None] + np.arange(window)[None, :]] * np.hanning(window).astype(np.float32)
    magnitude = np.abs(np.fft.rfft(frames, axis=1))
    frequencies = np.fft.rfftfreq(window, 1 / sample_rate)
    edges = np.geomspace(40.0, min(12000.0, sample_rate / 2 * 0.9), bands + 1)
    mask = np.zeros((len(frequencies), bands), dtype=np.float32)
    for band in range(bands):
        members = np.where((frequencies >= edges[band]) & (frequencies < edges[band + 1]))[0]
        if len(members) == 0:
            # Log spacing can be finer than the FFT resolution: snap to the closest bin
            # so no band is left dead.
            members = np.array([int(np.argmin(np.abs(frequencies - (edges[band] + edges[band + 1]) / 2)))])
        mask[members, band] = 1.0
    power = (magnitude**2) @ mask
    rms = np.sqrt(power / np.maximum(mask.sum(axis=0), 1))
    return rms, edges


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", type=Path, default=DEFAULT_AUDIO)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--waveform-rate", type=float, default=100.0, help="Envelope points per second.")
    parser.add_argument("--spectrum-rate", type=float, default=60.0, help="Spectrum frames per second; match the video frame rate.")
    parser.add_argument("--bands", type=int, default=32)
    parser.add_argument("--window", type=int, default=2048, help="FFT window in samples.")
    parser.add_argument("--sample-rate", type=int, default=44100)
    args = parser.parse_args()

    samples = decode(args.audio, args.sample_rate)
    duration = len(samples) / args.sample_rate

    low, high = envelope(samples, args.sample_rate, args.waveform_rate)
    write_json(
        args.output_dir / "waveform.json",
        {
            "version": 1,
            "audio": str(args.audio.relative_to(ROOT)).replace("\\", "/"),
            "rate": args.waveform_rate,
            "duration": round(duration, 3),
            "peak": round(float(max(abs(low.min()), abs(high.max()))), 4),
            "min": [round(float(value), 4) for value in low],
            "max": [round(float(value), 4) for value in high],
        },
    )

    rms, edges = spectrum(samples, args.sample_rate, args.spectrum_rate, args.bands, args.window)
    reference = float(np.percentile(rms, 99.5)) or float(rms.max())
    decibels = 20 * np.log10(np.maximum(rms, 1e-9) / reference)
    level = np.clip((decibels - SPECTRUM_FLOOR_DB) / -SPECTRUM_FLOOR_DB, 0.0, 1.0)
    write_json(
        args.output_dir / "spectrum.json",
        {
            "version": 1,
            "audio": str(args.audio.relative_to(ROOT)).replace("\\", "/"),
            "rate": args.spectrum_rate,
            "bands": args.bands,
            "floor_db": SPECTRUM_FLOOR_DB,
            "reference_percentile": 99.5,
            "encoding": "base64-uint8",
            "band_edges_hz": [round(float(edge), 1) for edge in edges],
            "data": base64.b64encode(np.round(level * 255).astype(np.uint8).tobytes()).decode("ascii"),
        },
    )
    print(f"Wrote {len(low)} envelope points and {len(level)}x{args.bands} spectrum frames to {args.output_dir}")


if __name__ == "__main__":
    main()
