#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PYTHON="${VIRTUAL_ENV:-$ROOT/.venv}/bin/python"

usage() {
  cat <<'EOF'
Usage: tts [options] INPUT.txt|INPUT.md

Defaults: INPUT.wav beside input, af_heart voice, speed 1.0, 400-char chunks.
Options:
  -o, --output FILE       Output WAV path
  -v, --voice NAME        Voice (default: af_heart)
  -s, --speed NUMBER      Speech speed (default: 1.0)
  -c, --max-chars NUMBER  Target maximum characters per chunk (default: 400)
  -d, --device DEVICE     cpu, cuda, or mps (default: cpu)
      --markdown MODE     auto, on, or off (default: auto)
      --skip-tables       Do not speak Markdown tables
      --read-code         Read fenced code rather than omit it
      --resume            Resume compatible interrupted synthesis
      --keep-segments     Keep checkpoint WAVs and status JSON after success
  -h, --help              Show this help
EOF
}

args=()
while (($#)); do
  case "$1" in
    -o|--output|-v|--voice|-s|--speed|-c|--max-chars|-d|--device|--markdown) [[ $# -ge 2 ]] || { echo "missing value for $1" >&2; exit 2; }; args+=("$1" "$2"); shift 2 ;;
    --skip-tables|--read-code|--resume|--keep-segments) args+=("$1"); shift ;;
    -h|--help) usage; exit 0 ;;
    --) shift; args+=("$@"); break ;;
    -*) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    *) args+=("$1"); shift ;;
  esac
done
[[ -x "$PYTHON" ]] || { echo "Environment is not ready. Run: source $ROOT/sourceme.bash" >&2; exit 1; }
exec "$PYTHON" "$ROOT/kokoro_tts.py" "${args[@]}"
