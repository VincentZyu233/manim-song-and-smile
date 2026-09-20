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

## 🎞️ Render

Pass a local LXGW WenKai Medium TTF via `--path` and a scratch directory via `--work`. The font is
registered from the file, with no system-font fallback. Personal paths belong only in the ignored AGENTS.local.md.

```powershell
uv run python scripts/render.py --quality preview --duration 55 --path "<LXGWWenKai-Medium.ttf>" --work "<scratch directory>"
uv run python scripts/render.py --quality final --path "<LXGWWenKai-Medium.ttf>" --work "<scratch directory>"
uv run python scripts/validate.py output/song-and-smile.mp4
```

A preview is intentionally cut to the requested number of seconds; `final` renders the full 161-second
scene and uses FFmpeg to mux the original MP3 with the video.

## 🎨 Design rules

Lyrics are warm white by default. Stable semantic colors make ending words part of the scene rather than decorative karaoke highlighting:

- `home`: amber
- `keep` / `smile`: coral
- `song` / `horizon`: sky cyan
- `spring flower`: leaf green

Titles and lyric phrases are drawn with `Write`. The top waveform and the bottom plant line art
have been removed; the closing smile arc keeps `Create`.

A phrase head starts drawing `LEAD_IN` (0.30 s) before its cue start and the outgoing phrase has already
finished fading out, so a line no longer waits for the previous fade. A colored ending word starts drawing
`KEYWORD_LEAD` (1 s) before its recorded `keyword_start` but still finishes at `keyword_start + KEYWORD_TAIL`
(0.85 s) — exactly where it finished before — so the pen stroke is visible instead of snapping on at the
sung syllable, without changing when the word is complete. These are animation pre-rolls only: the timeline still decides when every cue may start.

## 📄 License

Source code is released under the [MIT license](LICENSE). The music, lyrics and any rendered video in
this repository are **not** covered by MIT; their rights are described in [ASSET_NOTICE.md](ASSET_NOTICE.md).
