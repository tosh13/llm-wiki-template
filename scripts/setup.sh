#!/bin/bash
# setup.sh — llm-wiki 環境の初回セットアップ
# 冪等（再実行可）。--migrate-existing で既存環境からの移行に対応。

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

VERSION="0.1.0"
TEMPLATE_ROOT="$(template_root "${BASH_SOURCE[0]}")"

# Parse flags
DRY_RUN=0
MIGRATE_EXISTING=0
WIRE_ONLY=0
WIKI_NAME="llm-wiki"
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --migrate-existing) MIGRATE_EXISTING=1 ;;
        --wire-only) WIRE_ONLY=1 ;;
        --wiki-name=*) WIKI_NAME="${arg#--wiki-name=}" ;;
        --help|-h)
            cat <<EOF
Usage: $0 [options]

Options:
  --dry-run             変更を加えず、何が起こるかを表示
  --migrate-existing    既存の ~/llm-wiki/ を template 管理に切り替える
  --wire-only           vault の中身に触らず、この端末の配線だけを行う
                        （2台目以降。vault は iCloud で共有される実体なので、
                          中身を書き換えると他の端末へ波及する）
  --wiki-name=NAME      vault 名を指定（既定: llm-wiki）
  --help, -h            このヘルプを表示
EOF
            exit 0
            ;;
        *)
            err "不明なオプション: $arg"
            exit 1
            ;;
    esac
done

info "===== llm-wiki セットアップ v$VERSION ====="
info "テンプレート: $TEMPLATE_ROOT"
info "Vault名: $WIKI_NAME"
[ "$DRY_RUN" = "1" ] && warn "DRY RUN モード: 変更は加えません"
[ "$MIGRATE_EXISTING" = "1" ] && warn "MIGRATE モード: 既存ファイルを上書きします（確認あり）"
[ "$WIRE_ONLY" = "1" ] && warn "WIRE-ONLY モード: vault の中身には触れず、この端末の配線だけを行います"

# ===== Step 1: 前提チェック =====
info ""
info "Step 1/12: 前提チェック"
check_macos
check_command claude "https://docs.anthropic.com/claude/docs/claude-code を参照" || exit 1
if [ ! -d "/Applications/Obsidian.app" ] && [ ! -d "$HOME/Applications/Obsidian.app" ]; then
    warn "Obsidian.app が見つかりません。https://obsidian.md からインストールしてください"
fi
if [ ! -d "$HOME/Library/Mobile Documents/com~apple~CloudDocs" ]; then
    err "iCloud Drive が有効化されていないようです"
    err "システム設定 → Apple ID → iCloud → iCloud Drive を ON にしてください"
    exit 1
fi
ok "iCloud Drive 確認"

# ===== Step 2: vault パス決定 =====
VAULT_PATH="$(icloud_vault_path "$WIKI_NAME")"
SYMLINK_PATH="$HOME/$WIKI_NAME"

info ""
info "Step 2/12: vault パス"
info "  実体:    $VAULT_PATH"
info "  symlink: $SYMLINK_PATH"

# vault は iCloud で全端末が共有する1つの実体。2台目以降で中身を書き換えると
# 他の端末へ波及する（Step 6 の CLAUDE.md 置換、Step 12 の receipt がこれに当たる）。
# 既に構築済みの vault を見つけたら、配線だけに絞るよう促す。
if [ "$WIRE_ONLY" = "0" ] && [ -f "$VAULT_PATH/index.md" ]; then
    warn "この vault は既に構築済みです（別の端末が作ったものが iCloud で降りている）"
    warn "vault は全端末で共有される1つの実体なので、中身を書き換えると他の端末へ波及します"
    warn "2台目以降は --wire-only を付けてください（配線だけを行い、vault には触れません）"
fi

# ===== Step 3: ディレクトリツリー作成 =====
info ""
info "Step 3/12: ディレクトリツリー作成"
if [ "$WIRE_ONLY" = "1" ]; then
    ok "skip（--wire-only）"
elif [ "$DRY_RUN" = "0" ]; then
    mkdir -p "$VAULT_PATH"/sources/handoffs \
             "$VAULT_PATH"/sources/papers \
             "$VAULT_PATH"/sources/references \
             "$VAULT_PATH"/sources/clippings \
             "$VAULT_PATH"/wiki/concepts \
             "$VAULT_PATH"/wiki/entities \
             "$VAULT_PATH"/wiki/synthesis
fi
ok "ディレクトリ作成"

# ===== Step 4: ~/llm-wiki symlink =====
info ""
info "Step 4/12: ~/$WIKI_NAME symlink"
if [ "$DRY_RUN" = "0" ]; then
    if [ "$MIGRATE_EXISTING" = "1" ]; then
        safe_symlink "$VAULT_PATH" "$SYMLINK_PATH" --force
    else
        safe_symlink "$VAULT_PATH" "$SYMLINK_PATH"
    fi
fi

# ===== Step 5: seed/ をコピー（既存はskip） =====
info ""
info "Step 5/12: seed/ をコピー（既存ファイルはskip）"
if [ "$WIRE_ONLY" = "1" ]; then
    ok "skip（--wire-only）"
elif [ "$DRY_RUN" = "0" ]; then
    # トップレベルの index.md, log.md
    for name in index.md log.md; do
        src="$TEMPLATE_ROOT/seed/$name"
        target="$VAULT_PATH/$name"
        if [ ! -e "$target" ]; then
            cp "$src" "$target"
            ok "コピー: $name"
        else
            ok "既存(skip): $name"
        fi
    done
    # log.md の YYYY-MM-DD 置換（初回のみ）
    if [ -f "$VAULT_PATH/log.md" ] && grep -q "YYYY-MM-DD wiki初期化" "$VAULT_PATH/log.md"; then
        today=$(date +%Y-%m-%d)
        sed -i.bak "s/YYYY-MM-DD wiki初期化/$today wiki初期化/" "$VAULT_PATH/log.md"
        rm "$VAULT_PATH/log.md.bak"
        ok "log.md の日付を $today に置換"
    fi
    # seed/wiki/concepts/ をコピー
    for src in "$TEMPLATE_ROOT/seed/wiki/concepts"/*.md; do
        name="$(basename "$src")"
        target="$VAULT_PATH/wiki/concepts/$name"
        if [ ! -e "$target" ]; then
            cp "$src" "$target"
            ok "コピー: wiki/concepts/$name"
        else
            ok "既存(skip): wiki/concepts/$name"
        fi
    done
fi

# ===== Step 6: schema/CLAUDE.md を vault に symlink =====
info ""
info "Step 6/12: schema/CLAUDE.md を vault に symlink"
if [ "$WIRE_ONLY" = "1" ]; then
    # vault の CLAUDE.md を symlink に置き換えると、リンク先はこの端末にしか
    # 存在しないパスなので、他の端末には壊れたリンクか通常ファイルとして降りる。
    ok "skip（--wire-only。vault の CLAUDE.md は共有実体なので触らない）"
elif [ "$DRY_RUN" = "0" ]; then
    if [ "$MIGRATE_EXISTING" = "1" ]; then
        safe_symlink "$TEMPLATE_ROOT/schema/CLAUDE.md" "$VAULT_PATH/CLAUDE.md" --force
    else
        safe_symlink "$TEMPLATE_ROOT/schema/CLAUDE.md" "$VAULT_PATH/CLAUDE.md"
    fi
fi

# ===== Step 7: schema/LLM-WIKI.md を ~/.claude/ に symlink =====
info ""
info "Step 7/12: schema/LLM-WIKI.md を ~/.claude/ に symlink"
if [ "$DRY_RUN" = "0" ]; then
    mkdir -p "$HOME/.claude"
    safe_symlink "$TEMPLATE_ROOT/schema/LLM-WIKI.md" "$HOME/.claude/LLM-WIKI.md" --force
fi

# ===== Step 8: ~/.claude/CLAUDE.md に @LLM-WIKI.md 行を確保 =====
info ""
info "Step 8/12: ~/.claude/CLAUDE.md に @LLM-WIKI.md 行があるか確認"
GLOBAL_CLAUDE="$HOME/.claude/CLAUDE.md"
if [ "$DRY_RUN" = "0" ]; then
    if [ ! -f "$GLOBAL_CLAUDE" ]; then
        echo "@LLM-WIKI.md" > "$GLOBAL_CLAUDE"
        ok "新規作成: $GLOBAL_CLAUDE"
    elif grep -qE "^@LLM-WIKI\.md[[:space:]]*$" "$GLOBAL_CLAUDE"; then
        ok "@LLM-WIKI.md 既存"
    else
        printf '\n@LLM-WIKI.md\n' >> "$GLOBAL_CLAUDE"
        ok "@LLM-WIKI.md 追記"
    fi
fi

# ===== Step 9: handoff prompt info =====
info ""
info "Step 9/12: handoff prompt"
ok "ChatGPT/Geminiでの利用時は次のファイルを参照: $TEMPLATE_ROOT/prompts/handoff-prompt.md"

# ===== Step 10: Web Clipper 設定インポート手順 =====
info ""
info "Step 10/12: Web Clipper 設定インポート手順（手動）"
cat <<EOF

  1. Chrome に Obsidian Web Clipper 拡張をインストール:
     https://chromewebstore.google.com/detail/obsidian-web-clipper/cnjifjpddelmedmihgijeibhnjfabdlf
  2. 拡張のオプション → Settings → Advanced → Import all settings
  3. 以下のファイルを選択:
     $TEMPLATE_ROOT/dotfiles/obsidian-web-clipper-settings.json
  4. Vault 名が "$WIKI_NAME" になっているか確認

EOF

# ===== Step 11: local-notes.md =====
info "Step 11/12: local-notes.md（個人メモ用、CLAUDE.md から @include）"
if [ "$WIRE_ONLY" = "1" ]; then
    ok "skip（--wire-only）"
elif [ "$DRY_RUN" = "0" ]; then
    if [ ! -f "$VAULT_PATH/local-notes.md" ]; then
        cat > "$VAULT_PATH/local-notes.md" <<'EOF'
# ローカルメモ

このファイルはCLAUDE.md から `@local-notes.md` でincludeされる個人メモ用ファイル。
gitに含まれないので、自分の環境固有の追加指示や将来Ingest候補の優先度を書ける。

## 例: 将来のIngest候補

（未記入）
EOF
        ok "新規作成: local-notes.md"
    else
        ok "既存: local-notes.md"
    fi
fi

# ===== Step 12: setup-receipt =====
info ""
info "Step 12/12: setup-receipt.json（update.sh が version 比較に使用）"
if [ "$WIRE_ONLY" = "1" ]; then
    # receipt は template_root に端末ごとのパスを持つ。vault は共有実体なので、
    # 2台目以降が書くと1台目の値を潰し、端末間で上書きし合う。
    ok "skip（--wire-only。既存の値を残す）"
elif [ "$DRY_RUN" = "0" ]; then
    cat > "$VAULT_PATH/.setup-receipt.json" <<EOF
{
  "version": "$VERSION",
  "setup_at": "$(date +%Y-%m-%dT%H:%M:%S%z)",
  "template_root": "$TEMPLATE_ROOT",
  "wiki_name": "$WIKI_NAME"
}
EOF
    ok "setup-receipt.json 書き込み"
fi

echo
ok "===== セットアップ完了 ====="
info "次のステップ:"
echo "  1. Obsidian で $SYMLINK_PATH を vault として開く"
echo "  2. iPhone/iPad の Obsidian でも同じ vault が見えるか確認"
echo "  3. claude を起動して 'llm-wikiについて教えて' で wiki/concepts/ が参照されるか確認"
echo "  4. story/design-rationale.md を読んで運用思想を学ぶ"
