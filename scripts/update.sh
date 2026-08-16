#!/bin/bash
# update.sh — テンプレートの最新版を pull して vault に同期
# schema/ は symlink のため自動反映。seed/ は新規追加のみコピー、既存編集は保護。

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

TEMPLATE_ROOT="$(template_root "${BASH_SOURCE[0]}")"
WIKI_NAME="${1:-llm-wiki}"
VAULT_PATH="$(icloud_vault_path "$WIKI_NAME")"

info "===== llm-wiki アップデート ====="
info "テンプレート: $TEMPLATE_ROOT"
info "Vault:        $VAULT_PATH"

if [ ! -d "$VAULT_PATH" ]; then
    err "vault が見つかりません: $VAULT_PATH"
    err "先に bash scripts/setup.sh を実行してください"
    exit 1
fi

# ===== Step 1: git pull =====
info ""
info "Step 1/4: テンプレートを git pull"
cd "$TEMPLATE_ROOT"
git pull --ff-only
ok "git pull 完了"

# ===== Step 2: バージョンチェック =====
info ""
info "Step 2/4: バージョンチェック"
RECEIPT="$VAULT_PATH/.setup-receipt.json"
SETUP_VERSION=$(grep '^VERSION=' "$SCRIPT_DIR/setup.sh" | head -1 | cut -d'"' -f2)
if [ -f "$RECEIPT" ]; then
    receipt_version=$(grep '"version"' "$RECEIPT" | sed 's/.*"version": *"\([^"]*\)".*/\1/')
    info "  setup-receipt: $receipt_version"
    info "  setup.sh:      $SETUP_VERSION"
    # major bump 検出（X.y.z の X が異なる）
    if [ "${receipt_version%%.*}" != "${SETUP_VERSION%%.*}" ]; then
        err "メジャーバージョン変更を検出しました（$receipt_version → $SETUP_VERSION）"
        err "README.md の MIGRATION セクションを参照してください"
        exit 2
    fi
fi

# ===== Step 3: seed/ の差分処理 =====
info ""
info "Step 3/4: seed/wiki/concepts/ の差分処理"
NEW_COUNT=0
EDITED_COUNT=0
for src in "$TEMPLATE_ROOT/seed/wiki/concepts"/*.md; do
    name="$(basename "$src")"
    target="$VAULT_PATH/wiki/concepts/$name"
    if [ ! -f "$target" ]; then
        cp "$src" "$target"
        ok "新規 seed コピー: wiki/concepts/$name"
        NEW_COUNT=$((NEW_COUNT + 1))
    else
        if ! diff -q "$src" "$target" >/dev/null 2>&1; then
            warn "wiki/concepts/$name は手動編集または旧版（上書きしません）"
            warn "  比較するには: diff \"$src\" \"$target\""
            EDITED_COUNT=$((EDITED_COUNT + 1))
        fi
    fi
done
info "新規ページ: $NEW_COUNT 件、差分あり: $EDITED_COUNT 件"

# ===== Step 4: Web Clipper 設定の差分 =====
info ""
info "Step 4/4: Web Clipper 設定の差分"
WC_SRC="$TEMPLATE_ROOT/dotfiles/obsidian-web-clipper-settings.json"
ok "テンプレ最新版: $WC_SRC"
info "  必要に応じて Chrome拡張のSettings → Import all settings から再インポート"

echo
ok "===== アップデート完了 ====="
info "schema/LLM-WIKI.md は symlink 経由で自動更新済み（schema/CLAUDE.md はこのリポジトリが正本なので配置は不要）"
info "次回 claude 起動時から新しい運用規約が反映されます"
