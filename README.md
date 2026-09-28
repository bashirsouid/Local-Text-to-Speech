# Local Text to Speech

Fully local, self-bootstrapping Kokoro-82M text-to-speech. Apache 2.0 model,
runs on CPU, ~330MB weights auto-downloaded on first run (offline after that).

On a standard consumer laptop, you can expect generation at roughly 2x real-time talking speed.

## Quick start

    sudo apt-get install -y espeak-ng python3-venv   # one-time system deps
    source sourceme.bash                             # creates venv, installs deps
    tts notes.txt                                    # -> notes.wav next to input

## Supported input formats

- `.txt` — plain text
- `.md` / `.markdown` — Markdown (tables skipped by default, code fences omitted by default; configurable via `--markdown`, `--skip-tables`, `--read-code`)
- A directory — all `.md`/`.markdown` files in sorted order, producing one WAV beside each file; use `--single-file` to combine them into one WAV.

## Daily use

    source sourceme.bash        # activates env (instant once set up)
    tts article.txt             # writes article.wav
    tts --voice af_bella --speed 1.1 article.txt
    tts -o out/talk.wav talk.txt
    tts --resume longbook.txt   # resume an interrupted run from checkpoints
    tts notes/                    # notes/one.wav, notes/two.wav, ...
    tts --single-file notes/ -o notes.wav

Flags: --voice --lang --speed --max-chars --device cpu|cuda
       --keep-segments --resume --single-file -o/--output

For directory input, `-o/--output` names the output directory in normal mode,
or the combined WAV path with `--single-file`.

## Layout

    sourceme.bash      source this: builds/activates .venv, installs deps
    tts.bash           front-end wrapper (also callable directly, no source needed)
    kokoro_tts.py      engine: batching, checkpointing, resume
    requirements.txt   python deps (torch installed separately by sourceme.bash)
    .venv/             created on first source
    <out>.kokoro-status/   per-run checkpoints + status.json (auto-cleaned)

## Portability

Move the whole folder anywhere, then `source sourceme.bash` again. The venv is
health-checked on every source (verifies sys.prefix, not just path existence);
if the move invalidated it, it is rebuilt automatically. The wrapper scripts
resolve their own location, so no hardcoded paths anywhere.

Env vars for sourceme.bash:
    WITH_CUDA=1        install CUDA torch instead of CPU-only wheel
    KOKORO_REBUILD=1   force-recreate the venv
    KOKORO_LOCAL_HF=1  keep the HF model cache inside the project (.hf/)

## Voices

Default af_heart (best American female). Also: af_bella, af_nicole, am_michael,
am_adam; British: bf_emma, bf_isabella, bm_george. Match --lang to the voice
prefix (a = American, b = British).

## Notes

- Long texts are split into ~400-char sentence-aligned batches (Kokoro's
  quality sweet spot is 100-200 tokens); each batch is checkpointed so
  interrupted runs resume with --resume.
- Output is 24kHz WAV. Convert with ffmpeg if you want mp3/opus.
- espeak-ng is a hard dependency (grapheme-to-phoneme).
