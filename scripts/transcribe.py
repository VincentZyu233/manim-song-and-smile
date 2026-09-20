"""Generate a Whisper candidate transcript for timing quality assurance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIO = ROOT / "music" / "歌声与微笑.mp3"
DEFAULT_OUTPUT = ROOT / "build" / "whisper-candidate.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", type=Path, default=DEFAULT_AUDIO)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    args = parser.parse_args()

    from faster_whisper import WhisperModel

    device = "cuda" if args.device in ("auto", "cuda") else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    try:
        model = WhisperModel(args.model, device=device, compute_type=compute_type)
    except Exception:
        if args.device != "auto":
            raise
        device, compute_type = "cpu", "int8"
        model = WhisperModel(args.model, device=device, compute_type=compute_type)
    segments, info = model.transcribe(str(args.audio), language="zh", beam_size=5, word_timestamps=True, vad_filter=False)
    payload = {"model": args.model, "device": device, "language": info.language, "duration": info.duration, "segments": []}
    for segment in segments:
        payload["segments"].append({
            "start": round(segment.start, 3), "end": round(segment.end, 3), "text": segment.text.strip(),
            "words": [{"start": round(word.start, 3), "end": round(word.end, 3), "word": word.word, "probability": round(word.probability, 3)} for word in (segment.words or [])],
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(payload['segments'])} candidate segments to {args.output}")


if __name__ == "__main__":
    main()

