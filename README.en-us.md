# 🎬 Song and Smile Lyric Garden

A 9:16 Manim lyric video for `Song and Smile`: LXGW WenKai, `Write` animation,
and semantic keyword colors on a clean dark background.

> **[📖 English](README.en-us.md)**
> **[📖 简体中文(大陆)](README.md)**

## ⚖️ Assets and attribution

- Lyrics: Wang Jian
- Music: Gu Jianfen
- Performance: Crescent Choir

The audio and lyrics were obtained through QQ Music, **without a redistribution license from the rights holders**, and are
included for personal study and appreciation only; all rights stay with them. Keep the attribution above and the assets will be removed if a rights holder objects — see [ASSET_NOTICE.md](ASSET_NOTICE.md).

## ⚙️ Setup

Requires Python 3.12 or 3.13, FFmpeg, and a CJK font. The commands below go through a local
HTTP proxy when downloading Python packages or Whisper models.

```powershell
$env:HTTP_PROXY = "http://127.0.0.1:7890"
$env:HTTPS_PROXY = "http://127.0.0.1:7890"
uv sync
```

## ⏱️ Build the timeline

The source LRC lives in `music/`. Re-import it whenever the LRC changes:

```powershell
uv run python scripts/import_lrc.py
uv run python scripts/analyze_audio.py
uv run python scripts/review_timeline.py
```

Open `build/timeline-review.html` in a browser: it plays the MP3, shows every line timing, and can export
the corrected JSON. After review, replace `assets/lyrics/timeline.json` with the exported file.

`faster-whisper` is only an optional quality check, not the source of the lyric timings:

```powershell
uv run python scripts/transcribe.py --model large-v3 --device auto
```

An RTX 3060 12 GB can run `large-v3` with CUDA; the first run downloads the model. For music, compare the
candidate transcript with the LRC instead of applying its timestamps blindly.

## 🎚️ Visualisation data

The spectrum bars and the envelope waveform both follow the real audio; the data is decoded with FFmpeg and committed:

```powershell
uv run python scripts/extract_audio.py
```

`assets/audio/waveform.json` holds the min/max envelope of the whole song (100 points per second) and
`assets/audio/spectrum.json` holds a per-frame 32 band spectrum (60 frames per second, base64 uint8). Re-run it after the audio changes.

## 🎞️ Render

Pass a local LXGW WenKai Medium TTF via `--path` and a scratch directory via `--work`. The font is
registered from the file, with no system-font fallback. Personal paths belong only in the ignored AGENTS.local.md.

```powershell
uv run python scripts/render.py --quality preview --duration 55 --path "<LXGWWenKai-Medium.ttf>" --work "<scratch directory>"
uv run python scripts/render.py --quality final --path "<LXGWWenKai-Medium.ttf>" --work "<scratch directory>"
uv run python scripts/validate.py output/song-and-smile.mp4
```

`--waveform` picks the top visualisation (`bars` reacting spectrum / `static` whole song envelope / `scroll` scrolling
envelope), `--bottom` adds the whole song envelope above the progress bar and `--fps` sets the frame rate (default 60).
A preview is cut to the requested seconds; `final` renders the full 161-second scene and muxes the original MP3.

## 🎨 Design rules

Lyrics are warm white by default. Stable semantic colors make ending words part of the scene rather than decorative karaoke highlighting:

- `home`: amber
- `keep` / `smile`: coral
- `song` / `horizon`: sky cyan
- `spring flower`: leaf green

Titles and lyric phrases are drawn with `Write`; the bottom plant line art stays removed and the closing smile arc keeps `Create`.

The top is a reacting spectrum that jumps with the music, each bar carrying a slowly falling peak hold cap; below it sit the
whole song envelope (played part coloured, amber dot on the playhead), the progress bar and a `m:ss.d / total` clock. All of
them read the render clock, so they stay in sync and keep drifting even through sustained notes. The closing title and smile arc fade out over `OUTRO_FADE` (3 s) and stop on the last frame.

A phrase head starts drawing `LEAD_IN` (0.30 s) before its cue start and the outgoing phrase has already
finished fading out, so a line no longer waits for the previous fade. A colored ending word starts drawing
`KEYWORD_LEAD` (1 s) before its recorded `keyword_start` but still finishes at `keyword_start + KEYWORD_TAIL`
(0.85 s) — exactly where it finished before — so the pen stroke is visible instead of snapping on at the
sung syllable, without changing when the word is complete. These are animation pre-rolls only: the timeline still decides when every cue may start.

## 📄 License

Source code is released under the [MIT license](LICENSE). The music, lyrics and any rendered video in
this repository are **not** covered by MIT; their rights are described in [ASSET_NOTICE.md](ASSET_NOTICE.md).
