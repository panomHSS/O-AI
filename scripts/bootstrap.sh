#!/usr/bin/env sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repository_root"

[ -f .env ] || cp .env.example .env
[ -f frontend/.env.local ] || cp frontend/.env.example frontend/.env.local

python_command="${PYTHON_BIN:-python3}"
command -v "$python_command" >/dev/null 2>&1 || {
  echo "Python 3.14 must be installed and available as '$python_command'." >&2
  exit 1
}

if [ ! -x .venv/bin/python ]; then
  "$python_command" -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r backend/requirements.txt
npm --prefix frontend ci
