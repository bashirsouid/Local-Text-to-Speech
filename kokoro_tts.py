#!/usr/bin/env python3
import argparse, hashlib, json, re, sys, time
from pathlib import Path
import numpy as np
import soundfile as sf
from markdown_it import MarkdownIt


def markdown_to_speech(text, skip_tables=False, read_code=False):
    md = MarkdownIt("commonmark").enable("table")
    tokens = md.parse(text)
    out, i = [], 0
    def clean(s):
        s = re.sub(r"!\[([^]]*)\]\([^)]+\)", r"Image: \1", s)
        s = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", s)
        s = re.sub(r"[*_`~]+", "", s)
        return re.sub(r"\s+", " ", s).strip()
    while i < len(tokens):
        t = tokens[i]
        if t.type == "heading_open":
            level = t.tag[1:]
            if i + 1 < len(tokens): out.append(f"Heading {level}. {clean(tokens[i+1].content)}.")
        elif t.type == "paragraph_open" and i + 1 < len(tokens):
            s = clean(tokens[i+1].content)
            if s: out.append(s)
        elif t.type == "fence":
            lang = t.info.strip() or "plain text"
            out.append(clean(t.content) if read_code else f"Code block ({lang}) omitted.")
        elif t.type == "bullet_list_open":
            j, n = i + 1, 0
            while j < len(tokens) and tokens[j].type != "bullet_list_close":
                if tokens[j].type == "inline":
                    s = clean(tokens[j].content)
                    if s: n += 1; out.append(f"Bullet {n}. {s}.")
                j += 1
            i = j
        elif t.type == "ordered_list_open":
            j, n = i + 1, int(t.attrGet("start") or 1)
            while j < len(tokens) and tokens[j].type != "ordered_list_close":
                if tokens[j].type == "inline":
                    s = clean(tokens[j].content)
                    if s: out.append(f"Item {n}. {s}."); n += 1
                j += 1
            i = j
        elif t.type == "table_open":
            j, rows = i + 1, []
            while j < len(tokens) and tokens[j].type != "table_close":
                if tokens[j].type == "tr_open":
                    cells, k = [], j + 1
                    while k < len(tokens) and tokens[k].type != "tr_close":
                        if tokens[k].type == "inline": cells.append(clean(tokens[k].content)[:200])
                        k += 1
                    if cells: rows.append(cells)
                j += 1
            if not skip_tables and rows:
                headers, data = rows[0], rows[1:]
                if len(data) > 100: out.append(f"Table with {len(data)} rows omitted because it is too large.")
                else:
                    out.append(f"Table with {len(data)} rows and {len(headers)} columns.")
                    for num, row in enumerate(data, 1):
                        pairs = [f"{headers[x] if x < len(headers) else 'Column '+str(x+1)}: {v}" for x, v in enumerate(row)]
                        out.append(f"Row {num}. " + ", ".join(pairs) + ".")
            i = j
        i += 1
    return "\n\n".join(out)


def chunks(text, maxchars):
    paras = re.split(r"\n\s*\n", text.strip())
    result, current = [], ""
    for p in paras:
        sentences = re.split(r"(?<=[.!?])\s+", p)
        for s in sentences:
            if len(current) + len(s) + 1 > maxchars and current:
                result.append(current.strip()); current = ""
            current += (" " if current else "") + s
    if current.strip(): result.append(current.strip())
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path); p.add_argument("-o", "--output", type=Path)
    p.add_argument("-v", "--voice", default="af_heart"); p.add_argument("-s", "--speed", type=float, default=1.0)
    p.add_argument("-c", "--max-chars", type=int, default=400); p.add_argument("-d", "--device", default="cpu")
    p.add_argument("--markdown", choices=("auto", "on", "off"), default="auto")
    p.add_argument("--skip-tables", action="store_true"); p.add_argument("--read-code", action="store_true")
    p.add_argument("--resume", action="store_true"); p.add_argument("--keep-segments", action="store_true")
    a = p.parse_args()
    if not a.input.is_file(): p.error(f"not a file: {a.input}")
    if a.max_chars < 50: p.error("--max-chars must be at least 50")
    output = a.output or a.input.with_suffix(".wav")
    raw = a.input.read_text(encoding="utf-8")
    is_md = a.markdown == "on" or (a.markdown == "auto" and a.input.suffix.lower() in (".md", ".markdown"))
    text = markdown_to_speech(raw, a.skip_tables, a.read_code) if is_md else raw
    parts = chunks(text, a.max_chars)
    if not parts: p.error("input has no speakable text")
    state_dir = Path(str(output) + ".kokoro-status"); state_dir.mkdir(parents=True, exist_ok=True)
    config = {"input_hash": hashlib.sha256(text.encode()).hexdigest(), "voice": a.voice, "speed": a.speed, "parts": len(parts), "device": a.device}
    status_path = state_dir / "status.json"
    if status_path.exists():
        old = json.loads(status_path.read_text())
        if old.get("config") != config:
            if a.resume: p.error("resume state does not match this input/options; remove the status directory or omit --resume")
            for f in state_dir.glob("segment-*.wav"): f.unlink()
    elif a.resume: print("[status] no prior checkpoint; starting fresh")
    status_path.write_text(json.dumps({"config": config, "completed": []}, indent=2))
    print(f"[input] {len(parts)} chunks; markdown={'yes' if is_md else 'no'}")
    from kokoro import KPipeline
    pipeline = KPipeline(lang_code=a.voice[0], device=a.device)
    rate = 24000
    for n, part in enumerate(parts):
        segment = state_dir / f"segment-{n:05d}.wav"
        if segment.exists(): print(f"[status] {n+1}/{len(parts)} cached"); continue
        started = time.monotonic(); audio_parts = []
        for _, _, audio in pipeline(part, voice=a.voice, speed=a.speed): audio_parts.append(np.asarray(audio, dtype=np.float32))
        audio = np.concatenate(audio_parts) if audio_parts else np.zeros(1, dtype=np.float32)
        sf.write(segment, audio, rate)
        elapsed = time.monotonic() - started; duration = len(audio) / rate
        status_path.write_text(json.dumps({"config": config, "completed": n + 1, "last_chunk_seconds": duration, "last_elapsed_seconds": elapsed}, indent=2))
        print(f"[status] {n+1}/{len(parts)} done: {duration:.1f}s audio in {elapsed:.1f}s")
    audio = [sf.read(state_dir / f"segment-{n:05d}.wav", dtype="float32")[0] for n in range(len(parts))]
    sf.write(output, np.concatenate(audio), rate)
    print(f"[done] wrote {output}")
    if not a.keep_segments:
        import shutil; shutil.rmtree(state_dir)

if __name__ == "__main__": main()
