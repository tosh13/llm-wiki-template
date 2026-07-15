# 前提準備チェックリスト

`scripts/setup.sh` を走らせる前に、以下が揃っているか確認すること。
人間判断が必要なため、スクリプトでは自動化していない。

## 1. Anthropic アカウントと Claude Code

- [ ] Anthropic アカウントを作成: https://console.anthropic.com/
- [ ] Claude Code の課金プランを選ぶ
  - **Claude Pro**（月額$20）— 個人利用、月間使用量に上限あり
  - **Claude Max**（月額$100以上）— ヘビーユーザー向け
  - 詳細: https://claude.com/pricing
- [ ] Claude Code CLI をインストール: https://docs.claude.com/en/docs/claude-code/setup
  ```bash
  npm install -g @anthropic-ai/claude-code
  # 認証
  claude login
  ```
- [ ] `claude --version` でバージョンが表示されることを確認

## 2. GitHub アカウント

- [ ] GitHub アカウントを作成: https://github.com/join
- [ ] SSH キーまたは GitHub CLI で認証設定
  - GitHub CLI: `brew install gh && gh auth login`
- [ ] このリポジトリを clone できることを確認

## 3. iCloud Drive

- [ ] Apple ID でサインイン済み（システム設定 → Apple ID）
- [ ] iCloud Drive がオン（システム設定 → Apple ID → iCloud → iCloud Drive）
- [ ] **Advanced Data Protection** をオンにすることを推奨（E2E暗号化）
  - システム設定 → Apple ID → iCloud → Advanced Data Protection
  - 有効化には全 Apple デバイスが最新OSである必要がある
- [ ] iCloud のストレージに余裕がある（無料 5GB、必要なら課金）

## 4. Obsidian

- [ ] Mac 版 Obsidian をインストール: https://obsidian.md
- [ ] iPhone 版 Obsidian をインストール（App Store）
- [ ] iPad 版 Obsidian をインストール（必要なら）
- [ ] **iCloud Drive 経由の vault 同期**を有効化する（Obsidian の Sync 課金は不要）
  - iPhone/iPad の Obsidian の設定 → Files → "Use iCloud" を ON

## 5. Chrome ブラウザ

- [ ] Chrome がインストール済み（Web Clipper 用）
  - https://www.google.com/chrome
- [ ] **Web Clipper の拡張機能のインストールは setup.sh の中で案内される**ので、まだインストール不要

## 6. ターミナルアプリ

- [ ] iTerm2 を推奨（標準のTerminal.appでも動く）: https://iterm2.com
- [ ] zsh が動く（macOS 10.15以降は標準）
- [ ] `git --version` が動く（Xcode Command Line Tools か Homebrew で入る）

## 任意：tmux（推奨）

複数の Claude Code セッションを並行運用したい場合：

- [ ] tmux をインストール: `brew install tmux`

## 確認スクリプト

以下を順に実行して、すべて成功すれば準備完了：

```bash
# Claude Code
claude --version

# git
git --version

# Obsidian
ls /Applications/Obsidian.app

# iCloud Drive
ls ~/Library/Mobile\ Documents/com~apple~CloudDocs

# Obsidian iCloud Vault directory（Obsidianを一度起動すると自動生成される）
ls ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/ 2>/dev/null || echo "→ Obsidianを一度起動してください"
```

すべて確認できたら `bash scripts/setup.sh` に進む。
