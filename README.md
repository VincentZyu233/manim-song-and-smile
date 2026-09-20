**简体中文** | [English](README.en-us.md)

---

# 🎬 歌声与微笑 · Manim 歌词视频

用 Manim 制作的 9:16 竖屏歌词视频《歌声与微笑》：霞鹜文楷、`Write` 书写动画，
以及语义化关键词配色，深色纯色背景。

## ⚖️ 素材与署名

- 作词：王健
- 作曲：谷建芬
- 演唱：新月合唱团

仓库维护者已确认：仓库中附带的音频与歌词时间轴可公开再分发。请保留以上署名，
并把底层许可或授权来源记录到 [ASSET_NOTICE.md](ASSET_NOTICE.md)（**目前仍待补充**）。

## ⚙️ 环境准备

需要 Python 3.12 或 3.13、FFmpeg，以及一款中文字体。下面的命令在下载 Python 包或
Whisper 模型时走本机 HTTP 代理。

```powershell
$env:HTTP_PROXY = "http://127.0.0.1:7890"
$env:HTTPS_PROXY = "http://127.0.0.1:7890"
uv sync
```

## ⏱️ 构建时间轴

源 LRC 位于 `music/`。只要 LRC 有改动就重新导入：

```powershell
uv run python scripts/import_lrc.py
uv run python scripts/analyze_audio.py
uv run python scripts/review_timeline.py
```

用浏览器打开 `build/timeline-review.html`：它会播放 MP3、展示每句时间，并可导出
修正后的 JSON。校对完成后，用导出的文件替换 `assets/lyrics/timeline.json`。

`faster-whisper` 只是可选的质量校验，不是歌词的时间来源：

```powershell
uv run python scripts/transcribe.py --model large-v3 --device auto
```

RTX 3060 12 GB 可以用 CUDA 跑 `large-v3`，首次运行会下载模型。对音乐而言，应该把
候选转写与 LRC 相互对照，而不是直接套用它的时间戳。

## 🎞️ 渲染

用 `--path` 传入本机的霞鹜文楷 Medium TTF，用 `--work` 指定临时目录。字体从文件
注册，不使用系统字体回退。个人路径只写在被忽略的 AGENTS.local.md 里。

```powershell
uv run python scripts/render.py --quality preview --duration 55 --path "<LXGWWenKai-Medium.ttf>" --work "<临时目录>"
uv run python scripts/render.py --quality final --path "<LXGWWenKai-Medium.ttf>" --work "<临时目录>"
uv run python scripts/validate.py output/song-and-smile.mp4
```

预览会有意截断到指定秒数；`final` 渲染完整的 161 秒场景，并用 FFmpeg 把原始 MP3
与画面合流。

## 🎨 设计规则

歌词默认暖白色。固定的语义配色让句尾词成为画面的一部分，而不是装饰性的卡拉 OK 高亮：

- `home`（家）：琥珀色
- `keep` / `smile`（留下 / 微笑）：珊瑚红
- `song` / `horizon`（歌声 / 海角天涯）：天青
- `spring flower`（遍野春花）：叶绿

标题与歌词都用 `Write` 书写。顶部波形与底部植物线稿已移除，片尾微笑弧线保留
`Create`。

每句句首在 cue 时间前 `LEAD_IN`（0.30 s）起笔，上一句的淡出在此之前结束，因此不再
等待前一句淡出。染色词在记录的 `keyword_start` 前 `KEYWORD_LEAD`（1 s）起笔，但仍在
`keyword_start + KEYWORD_TAIL`（0.85 s）——与改动前完全相同——收笔：既让笔触看得见、
不再贴着唱字"啪"地出现，又不改变写完的时刻。这些只是动画预滚，每个 cue 何时开始
始终由时间轴决定。

## 📄 许可

源代码以 [MIT 许可](LICENSE)发布。仓库中的音乐、歌词以及渲染出的视频**不在 MIT
覆盖范围内**，其权利见 [ASSET_NOTICE.md](ASSET_NOTICE.md)。
