# Windows 版 前提準備とセットアップ

このテンプレートは macOS + iCloud Drive を前提に作られている（`prerequisites.md`・`scripts/setup.sh` は macOS 用）。Windows で構築する場合の読み替えと、手動セットアップ手順をここにまとめる。

中核（`schema/CLAUDE.md`・`schema/LLM-WIKI.md`・`seed/` の概念ページ・`prompts/handoff-prompt.md`・`story/design-rationale.md`）はただの markdown で OS 非依存。書き換わるのは「同期基盤」「symlink」「パス」「セットアップスクリプト」の4点だけである。

## macOS版からの読み替え早見

- iCloud Drive → **Obsidian Sync**（または Syncthing）。詳細は後述
- FileVault（ディスク暗号化） → **BitLocker**
- symlink → **copy 運用**（Windows では symlink の扱いが不安定なため）
- `~/.claude/CLAUDE.md` → `%USERPROFILE%\.claude\CLAUDE.md`
- `bash scripts/setup.sh` → 後述の PowerShell 手動手順
- iTerm2 / zsh → **Windows Terminal + PowerShell**

## 1. Anthropic アカウントと Claude Code

- [ ] Anthropic アカウントを作成: https://console.anthropic.com/
- [ ] Claude Code の課金プランを選ぶ（Claude Pro 月額$20 / Claude Max 月額$100〜）: https://claude.com/pricing
- [ ] Claude Code CLI をインストール（**Windows ネイティブ対応。WSL は必須ではない**）: https://docs.claude.com/en/docs/claude-code/setup
  ```powershell
  npm install -g @anthropic-ai/claude-code
  claude login
  ```
- [ ] `claude --version` が表示されることを確認

Node.js が無ければ先に https://nodejs.org からインストールする。

## 2. GitHub アカウント

- [ ] GitHub アカウントを作成: https://github.com/join
- [ ] GitHub CLI で認証: `winget install GitHub.cli` の後 `gh auth login`
- [ ] このテンプレートを clone できることを確認

## 3. 同期基盤

機密性モデルは「vault に git remote を付けない ＋ 同期先が E2E 暗号化」で成り立つ。iCloud の代わりに、**同期先も E2E であるもの**を選ぶ。

- **Obsidian Sync（推奨）** — 公式・有料だが E2E 暗号化。Windows・iPhone・iPad・Android を横断し、コンフリクト処理も堅い。iCloud を丸ごと置き換えられ、Windows では最も素直
  - [ ] Obsidian の Settings → Sync から有効化し、リモート vault を作成
- **Syncthing** — 無料・クラウド不経由の P2P。自分の端末間のみで同期。常時起動する端末が要る
- **OneDrive / Dropbox は非推奨** — 既定で E2E でなく事業者が鍵を持つ。さらに「Files On-Demand（オンデマンド）」のプレースホルダで Claude/Obsidian がファイルを掴めない事故が起きやすい。使う場合は該当フォルダを「常にこのデバイスに保持」に設定し、`sensitivity: confidential` のページは置かない運用に限定する

## 4. ディスク暗号化

- [ ] **BitLocker** を有効化（設定 → プライバシーとセキュリティ → デバイスの暗号化 / BitLocker）
- [ ] サインインを生体認証（Windows Hello）またはパスワードで保護

## 5. Obsidian

- [ ] Windows 版 Obsidian をインストール: https://obsidian.md
- [ ] モバイルで見たい場合は iPhone/Android 版 Obsidian をインストールし、手順3で選んだ同期を有効化

## 6. Chrome ブラウザ

- [ ] Chrome をインストール: https://www.google.com/chrome
- [ ] Web Clipper 拡張は後の手順で入れるので今は不要

## 7. ターミナル

- [ ] **Windows Terminal + PowerShell** を使う（Windows 11 標準。無ければ Microsoft Store から）
- [ ] `git --version` が動く（`winget install Git.Git` で導入）

## 手動セットアップ手順

`setup.sh` は bash 用で Windows では動かない。PowerShell で以下を上から実行する。vault の置き場所は Obsidian Sync 管理下の任意フォルダでよい（例では `Documents\llm-wiki`）。

```powershell
# 変数
$Vault    = "$env:USERPROFILE\Documents\llm-wiki"
$Template = "$env:USERPROFILE\Projects\llm-wiki-template"   # clone 先に合わせる
$ClaudeD  = "$env:USERPROFILE\.claude"

# 1. vault のディレクトリツリー
$dirs = @(
  "sources\handoffs","sources\papers","sources\references","sources\clippings",
  "wiki\concepts","wiki\entities","wiki\synthesis"
)
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path (Join-Path $Vault $d) | Out-Null }

# 2. seed の初期ファイルをコピー（既存は上書きしない）
foreach ($f in @("index.md","log.md")) {
  $dst = Join-Path $Vault $f
  if (-not (Test-Path $dst)) { Copy-Item (Join-Path $Template "seed\$f") $dst }
}
Get-ChildItem "$Template\seed\wiki\concepts\*.md" | ForEach-Object {
  $dst = Join-Path $Vault "wiki\concepts\$($_.Name)"
  if (-not (Test-Path $dst)) { Copy-Item $_.FullName $dst }
}

# 3. 運用規約 schema/CLAUDE.md を vault に配置（copy 運用）
Copy-Item "$Template\schema\CLAUDE.md" (Join-Path $Vault "CLAUDE.md") -Force

# 4. 自動Ingest指示 schema/LLM-WIKI.md を ~/.claude に配置
New-Item -ItemType Directory -Force -Path $ClaudeD | Out-Null
Copy-Item "$Template\schema\LLM-WIKI.md" (Join-Path $ClaudeD "LLM-WIKI.md") -Force

# 5. グローバル CLAUDE.md に @LLM-WIKI.md 行を確保
$g = Join-Path $ClaudeD "CLAUDE.md"
if (-not (Test-Path $g)) { "@LLM-WIKI.md" | Set-Content $g -Encoding utf8 }
elseif (-not (Select-String -Path $g -Pattern '^@LLM-WIKI\.md\s*$' -Quiet)) {
  Add-Content $g "`n@LLM-WIKI.md"
}
```

`schema/CLAUDE.md` 末尾の `@local-notes.md` を使う場合は、vault 直下に `local-notes.md` を作る（無くても動作する）。

## Web Clipper 設定インポート

1. Chrome に Obsidian Web Clipper 拡張をインストール: https://chromewebstore.google.com/detail/obsidian-web-clipper/cnjifjpddelmedmihgijeibhnjfabdlf
2. 拡張のオプション → Settings → Advanced → Import all settings
3. `dotfiles\obsidian-web-clipper-settings.json` を選択
4. Vault 名が実際の vault 名と一致しているか確認

## copy 運用の継続同期

macOS 版は symlink で自動反映するが、Windows は copy 運用にした。テンプレートを更新したら手動セットアップ手順の 3〜4（`schema/CLAUDE.md`・`LLM-WIKI.md` のコピー）を再実行して反映する。

```powershell
cd $env:USERPROFILE\Projects\llm-wiki-template
git pull
Copy-Item "schema\CLAUDE.md" "$env:USERPROFILE\Documents\llm-wiki\CLAUDE.md" -Force
Copy-Item "schema\LLM-WIKI.md" "$env:USERPROFILE\.claude\LLM-WIKI.md" -Force
```

## 動作確認

```powershell
claude --version
git --version
Test-Path "$env:USERPROFILE\Documents\llm-wiki\CLAUDE.md"
Test-Path "$env:USERPROFILE\.claude\LLM-WIKI.md"
```

Obsidian で vault（例: `Documents\llm-wiki`）を開き、任意のフォルダで `claude` を起動して「llm-wikiについて教えて」で `wiki/concepts/` が参照されれば成功。
