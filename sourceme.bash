# Source this file: source sourceme.bash
# Uses a project-local uv and Python 3.12 because upstream Kokoro 0.9.4
# declares Requires-Python >=3.10,<3.13. Debian Trixie ships Python 3.13.

_kokoro_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)" || return 1
_kokoro_tools="$_kokoro_root/.tools/bin"
_kokoro_uv="$_kokoro_tools/uv"
_kokoro_venv="$_kokoro_root/.venv"
_kokoro_python="$_kokoro_venv/bin/python"

# Install uv into this project only when it is not already available. The official
# installer downloads its signed release artifact; no system Python/pip is touched.
if [[ ! -x "$_kokoro_uv" ]]; then
  mkdir -p "$_kokoro_tools" || return 1
  echo "[env] installing project-local uv bootstrapper"
  command -v curl >/dev/null || { echo "[env] curl is required to bootstrap uv" >&2; return 1; }
  curl --fail --location --silent --show-error https://astral.sh/uv/install.sh \
    | UV_INSTALL_DIR="$_kokoro_tools" UV_NO_MODIFY_PATH=1 sh || return 1
fi

_kokoro_rebuild=0
if [[ "${KOKORO_REBUILD:-0}" == "1" || ! -x "$_kokoro_python" ]]; then
  _kokoro_rebuild=1
elif ! "$_kokoro_python" -c 'import sys; assert sys.prefix != sys.base_prefix; assert sys.version_info[:2] == (3, 12)' >/dev/null 2>&1; then
  echo "[env] existing venv is not a usable Python 3.12 virtualenv; rebuilding"
  _kokoro_rebuild=1
fi

if (( _kokoro_rebuild )); then
  rm -rf -- "$_kokoro_venv"
  echo "[env] creating Python 3.12 environment (downloads Python once if needed)"
  "$_kokoro_uv" venv --python 3.12 --seed "$_kokoro_venv" || return 1
fi

_req_hash="$(sha256sum "$_kokoro_root/requirements.txt" | awk '{print $1}')"
_stamp="$_kokoro_venv/.requirements.sha256"
if [[ ! -f "$_stamp" || "$(cat "$_stamp" 2>/dev/null)" != "$_req_hash" ]]; then
  echo "[env] installing Python dependencies"
  "$_kokoro_uv" pip install --python "$_kokoro_python" -r "$_kokoro_root/requirements.txt" || return 1
  printf '%s\n' "$_req_hash" > "$_stamp"
fi

export VIRTUAL_ENV="$_kokoro_venv"
export PATH="$_kokoro_root:$VIRTUAL_ENV/bin:$PATH"
# Set KOKORO_LOCAL_HF=1 before sourcing to keep model downloads in the project.
if [[ "${KOKORO_LOCAL_HF:-0}" == "1" ]]; then export HF_HOME="$_kokoro_root/.hf"; fi

# Calling the wrapper by absolute, dynamically-derived path avoids old absolute
# shebang paths when this directory is moved.
tts() { "$_kokoro_root/tts.bash" "$@"; }

unset _kokoro_rebuild _req_hash _stamp
echo "[env] ready: Python 3.12 at $VIRTUAL_ENV"
echo "[env] run: tts INPUT.txt   (or INPUT.md)"
