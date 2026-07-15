#!/bin/bash
# common.sh — setup.sh / update.sh で共有するユーティリティ関数

# Colors (TTY のみ)
if [ -t 1 ]; then
    RED=$'\033[0;31m'
    YELLOW=$'\033[0;33m'
    GREEN=$'\033[0;32m'
    BLUE=$'\033[0;34m'
    BOLD=$'\033[1m'
    RESET=$'\033[0m'
else
    RED=""; YELLOW=""; GREEN=""; BLUE=""; BOLD=""; RESET=""
fi

info() { echo "${BLUE}[INFO]${RESET} $*"; }
warn() { echo "${YELLOW}[WARN]${RESET} $*" >&2; }
err()  { echo "${RED}[ERROR]${RESET} $*" >&2; }
ok()   { echo "${GREEN}[OK]${RESET} $*"; }

confirm() {
    local prompt="$1"
    local default="${2:-n}"
    local response
    if [ "$default" = "y" ]; then
        read -rp "${prompt} [Y/n]: " response
        response="${response:-y}"
    else
        read -rp "${prompt} [y/N]: " response
        response="${response:-n}"
    fi
    [[ "$response" =~ ^[yY]([eE][sS])?$ ]]
}

check_macos() {
    if [ "$(uname)" != "Darwin" ]; then
        err "このスクリプトはmacOSでのみ動作します（uname=$(uname)）"
        exit 1
    fi
    ok "macOS 確認"
}

check_command() {
    local cmd="$1"
    local hint="${2:-}"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        err "$cmd が見つかりません${hint:+: $hint}"
        return 1
    fi
    ok "$cmd 確認"
}

# テンプレートリポジトリのrootパスを返す
# 引数: 呼び出し元の "${BASH_SOURCE[0]}"
template_root() {
    local source_path="$1"
    local script_dir
    script_dir="$( cd "$( dirname "$source_path" )" && pwd )"
    if [[ "$script_dir" == */scripts/lib ]]; then
        echo "$( cd "$script_dir/../.." && pwd )"
    elif [[ "$script_dir" == */scripts ]]; then
        echo "$( cd "$script_dir/.." && pwd )"
    else
        echo "$script_dir"
    fi
}

# iCloud Drive 内の Obsidian vault パス（実体）
icloud_vault_path() {
    local vault_name="$1"
    echo "$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/$vault_name"
}

# 安全な symlink 作成
# 引数: src target [--force]
safe_symlink() {
    local src="$1"
    local target="$2"
    local force="${3:-}"

    if [ -L "$target" ]; then
        local current
        current="$(readlink "$target")"
        if [ "$current" = "$src" ]; then
            ok "symlink 既存: $target → $src"
            return 0
        fi
        warn "$target は別の場所への symlink です: $current"
        if [ "$force" != "--force" ] && ! confirm "上書きしますか？"; then
            return 1
        fi
        rm "$target"
    elif [ -e "$target" ]; then
        warn "$target は通常ファイル/ディレクトリとして既に存在します"
        if [ "$force" != "--force" ] && ! confirm "削除して symlink に置換しますか？"; then
            return 1
        fi
        rm -rf "$target"
    fi

    ln -s "$src" "$target"
    ok "symlink 作成: $target → $src"
}
