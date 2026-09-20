"""Build a self-contained browser page for reviewing cue boundaries."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TIMELINE = ROOT / "assets" / "lyrics" / "timeline.json"
DEFAULT_OUTPUT = ROOT / "build" / "timeline-review.html"


def page(timeline: dict, audio_relative: str) -> str:
    encoded = json.dumps(timeline, ensure_ascii=False)
    rows = "\n".join(
        f'<button class="cue" data-index="{index}"><b>{cue["start"]:06.2f}</b><span>{html.escape(cue["text"])}</span><i>{html.escape(cue["keyword"] or "-")}</i></button>'
        for index, cue in enumerate(timeline["cues"])
    )
    return f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Lyrics timeline review</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#0d1520;color:#f6f0e5;font:16px 'Microsoft YaHei',sans-serif}}main{{max-width:980px;padding:28px 20px 56px;margin:auto}}h1{{font-size:26px;margin:0 0 5px}}p{{color:#9cabb9;margin:5px 0 20px}}audio{{width:100%;margin:8px 0 20px}}#ruler{{position:relative;height:160px;border:1px solid #354556;background:repeating-linear-gradient(90deg,#111d2a 0,#111d2a calc(10% - 1px),#2c3c4b calc(10% - 1px),#2c3c4b 10%);overflow:hidden}}.bar{{position:absolute;height:18px;border-radius:2px;background:#72c8d4;opacity:.85;cursor:pointer}}.bar.keep,.bar.smile{{background:#ee786b}}.bar.home{{background:#f3c66a}}.bar.spring_flower{{background:#75c98d}}#cursor{{position:absolute;width:2px;top:0;bottom:0;background:white;pointer-events:none}}#editor{{display:grid;grid-template-columns:1fr 1fr auto;gap:10px;margin:20px 0}}input,button{{font:inherit}}input{{background:#172635;color:#f6f0e5;border:1px solid #52677c;padding:8px}}button{{border:0;cursor:pointer}}#export{{background:#f3c66a;color:#15202c;padding:8px 14px;font-weight:bold}}#cues{{display:grid;gap:4px}}.cue{{display:grid;grid-template-columns:78px 1fr 92px;text-align:left;padding:9px 11px;background:#142230;color:#f6f0e5;border-left:3px solid transparent}}.cue:hover,.cue.active{{background:#203649;border-left-color:#f3c66a}}.cue b{{color:#9cabb9;font-family:monospace}}.cue i{{color:#75c98d;font-style:normal;text-align:right}}</style>
<main><h1>歌词时间轴校对</h1><p>点击色块或列表条目，播放音频后调整开始和结束秒数。导出 JSON 后替换 <code>assets/lyrics/timeline.json</code>。</p><audio id="audio" controls src="../{html.escape(audio_relative)}"></audio><div id="ruler"><div id="cursor"></div></div><div id="editor"><input id="start" type="number" min="0" step="0.01" aria-label="开始秒数"><input id="end" type="number" min="0" step="0.01" aria-label="结束秒数"><button id="export">导出 JSON</button></div><div id="cues">{rows}</div></main>
<script>const timeline={encoded},audio=document.querySelector('#audio'),ruler=document.querySelector('#ruler'),cursor=document.querySelector('#cursor');let selected=0;function renderBars(){{ruler.querySelectorAll('.bar').forEach(n=>n.remove());timeline.cues.forEach((cue,i)=>{{const bar=document.createElement('button');bar.className='bar '+cue.keyword_kind;bar.title=cue.text;bar.style.left=(cue.start/timeline.duration*100)+'%';bar.style.width=Math.max(.4,(cue.end-cue.start)/timeline.duration*100)+'%';bar.style.top=(i%7*21+6)+'px';bar.onclick=()=>select(i);ruler.append(bar)}});document.querySelectorAll('.cue').forEach((row,i)=>row.classList.toggle('active',i===selected))}}function select(i){{selected=i;const cue=timeline.cues[i];document.querySelector('#start').value=cue.start;document.querySelector('#end').value=cue.end;audio.currentTime=cue.start;renderBars()}}function update(){{const cue=timeline.cues[selected],start=Number(document.querySelector('#start').value),end=Number(document.querySelector('#end').value);if(Number.isFinite(start)&&Number.isFinite(end)&&end>start){{cue.start=start;cue.end=end;cue.keyword_start=Math.min(Math.max(cue.keyword_start,start),end-.12);cue.reviewed=true;renderBars()}}}}document.querySelector('#start').onchange=update;document.querySelector('#end').onchange=update;document.querySelectorAll('.cue').forEach((row,i)=>row.onclick=()=>select(i));audio.ontimeupdate=()=>cursor.style.left=(audio.currentTime/timeline.duration*100)+'%';document.querySelector('#export').onclick=()=>{{const blob=new Blob([JSON.stringify(timeline,null,2)],{{type:'application/json'}}),link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='timeline.json';link.click();URL.revokeObjectURL(link.href)}};select(0)</script></html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeline", type=Path, default=DEFAULT_TIMELINE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    timeline = json.loads(args.timeline.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page(timeline, timeline["audio"]), encoding="utf-8")
    print(f"Wrote review page to {args.output}")


if __name__ == "__main__":
    main()
