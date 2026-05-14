#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

has_arg() {
  local name="$1"
  shift
  for item in "$@"; do
    if [[ "$item" == "$name" || "$item" == "$name="* ]]; then
      return 0
    fi
  done
  return 1
}

get_arg_value() {
  local name="$1"
  shift
  local items=("$@")
  local index=0
  while [[ $index -lt ${#items[@]} ]]; do
    local item="${items[$index]}"
    if [[ "$item" == "$name" ]]; then
      local next_index=$((index + 1))
      if [[ $next_index -ge ${#items[@]} ]]; then
        echo "Missing value for $name" >&2
        exit 1
      fi
      printf '%s\n' "${items[$next_index]}"
      return 0
    fi
    if [[ "$item" == "$name="* ]]; then
      printf '%s\n' "${item#*=}"
      return 0
    fi
    index=$((index + 1))
  done
  return 1
}

ensure_brew_shellenv() {
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
    return
  fi
  if [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
    return
  fi
}

install_homebrew() {
  NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ensure_brew_shellenv
}

ensure_homebrew() {
  if command -v brew >/dev/null 2>&1; then
    return
  fi
  ensure_brew_shellenv
  if command -v brew >/dev/null 2>&1; then
    return
  fi
  install_homebrew
  if ! command -v brew >/dev/null 2>&1; then
    echo "Failed to bootstrap Homebrew." >&2
    exit 1
  fi
}

ensure_formula() {
  local formula="$1"
  if brew list --versions "$formula" >/dev/null 2>&1; then
    return
  fi
  brew install "$formula"
}

ensure_git() {
  if command -v git >/dev/null 2>&1; then
    return
  fi
  ensure_homebrew
  ensure_formula git
}

ensure_python() {
  if command -v python3.11 >/dev/null 2>&1; then
    command -v python3.11
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return
  fi
  ensure_homebrew
  ensure_formula python@3.11
  if command -v python3.11 >/dev/null 2>&1; then
    command -v python3.11
    return
  fi
  command -v python3
}

ensure_node() {
  if command -v node >/dev/null 2>&1; then
    return
  fi
  ensure_homebrew
  ensure_formula node
}

EXPLICIT_PYTHON="$(get_arg_value --python "$@" || true)"
WITH_WEBSITE=false
if has_arg --with-website "$@"; then
  WITH_WEBSITE=true
fi

ensure_git
if [[ "$WITH_WEBSITE" == true ]]; then
  ensure_node
fi

PYTHON_BIN="${EXPLICIT_PYTHON:-$(ensure_python)}"
echo "Using Python: $PYTHON_BIN"

FORWARD_ARGS=("$@")
if [[ -z "$EXPLICIT_PYTHON" ]]; then
  FORWARD_ARGS+=("--python" "$PYTHON_BIN")
fi

"$PYTHON_BIN" "$SCRIPT_DIR/package_chattodo.py" "${FORWARD_ARGS[@]}"
