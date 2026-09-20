# Song and Smile Lyric Garden

A 9:16 Manim lyric video for `Song and Smile`, using LXGW WenKai,
Write animations and semantic keyword colors on a clean dark background.

## Assets and attribution

- Lyrics: Wang Jian
- Music: Gu Jianfen
- Performance: Crescent Choir

The repository maintainer has confirmed permission to redistribute the included
audio and lyric timeline. Keep the attribution above and record the underlying
license or permission source in [ASSET_NOTICE.md](ASSET_NOTICE.md) before a
public release.

## Setup

Install Python 3.12 or 3.13, FFmpeg, and a CJK font. The commands below use a
local HTTP proxy when downloading Python packages or Whisper models.

```powershell
$env:HTTP_PROXY = "http://127.0.0.1:7890"
$env:HTTPS_PROXY = "http://127.0.0.1:7890"
uv sync
```

## Build the timeline

The source LRC is in `music/`. Import it whenever the LRC changes:

```powershell
uv run python scripts/import_lrc.py
uv run python scripts/analyze_audio.py
uv run python scripts/review_timeline.py
```

Open `build/timeline-review.html` in a browser. It plays the MP3, displays the
line timings, and can export corrected JSON. Replace
`assets/lyrics/timeline.json` with that exported file after review.

`faster-whisper` is optional quality assurance, not the lyric source of truth:

```powershell
uv run python scripts/transcribe.py --model large-v3 --device auto
```

An RTX 3060 12 GB can run `large-v3` with CUDA. The first invocation downloads
the model. For music, compare the candidate transcript to the LRC rather than
blindly applying its timestamps.

## Render

Pass a local LXGW WenKai Medium TTF via `--path` and a scratch directory via
`--work`. The font is registered from the file; no system-font fallback is used.
Personal paths belong only in the ignored AGENTS.local.md.

```powershell
uv run python scripts/render.py --quality preview --duration 55 --path "<LXGWWenKai-Medium.ttf>" --work "<scratch directory>"
uv run python scripts/render.py --quality final --path "<LXGWWenKai-Medium.ttf>" --work "<scratch directory>"
uv run python scripts/validate.py output/song-and-smile.mp4
```

Preview output is intentionally limited to the requested number of seconds.
The final command renders the full 161-second scene and uses FFmpeg to mux the
original MP3 with the video.

## Design rules

Lyrics are warm white by default. Stable semantic colors make ending words
part of the scene rather than decorative karaoke highlighting:

- `home`: amber
- `keep` / `smile`: coral
- `song` / `far horizon`: sky cyan
- `spring flower`: leaf green

`Write` draws titles and lyric phrases. The top waveform and bottom plants
have been removed; `Create` remains for the closing smile arc.

A phrase head starts drawing `LEAD_IN` (0.30 s) before its cue start and the
outgoing phrase is faded out before that, so a line no longer waits for the
previous fade. A colored ending word starts drawing `KEYWORD_LEAD` (1 s) before
its recorded `keyword_start` but still finishes at
`keyword_start + KEYWORD_TAIL` (0.85 s) — exactly where it landed before — so the
pen stroke is visible instead of snapping on at the sung syllable, without
changing when the word is complete. These are animation pre-rolls only: the
timeline still decides when every cue may start.

## License

Source code is released under the [MIT license](LICENSE). The included music,
lyrics and any rendered video are **not** covered by MIT; their rights are
described separately in [ASSET_NOTICE.md](ASSET_NOTICE.md).
