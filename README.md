# llm-wiki-template

Claude Code + Obsidian + iCloud Drive で動く、個人用知識ベース（LLM Wiki）のテンプレート。
[Karpathy の LLM Wiki パターン](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) を実運用に落とし込んだもの。

このリポジトリを clone して `setup.sh` を走らせると、Claude が自律的に知識を蓄積・整理してくれる仕組みが手元のMacに展開される。

## 想定読者

- 自分用の知識ベースを LLM の支援で育てたい人
- macOS + iCloud Drive + Obsidian + Claude Code（CLI）の組み合わせが使える人

iPhone/iPad での閲覧も想定している。

## 5分セットアップ

### 前提準備

`prerequisites.md` をまず読むこと。Anthropic アカウント・Claude Code 課金プラン・GitHub アカウント・iCloud Drive 有効化・Obsidian インストールが必要。

**Windows で構築する場合は `prerequisites-windows.md` を読む**（iCloud → Obsidian Sync、FileVault → BitLocker への読み替えと、`setup.sh` に代わる PowerShell 手動手順を記載）。

### 1. テンプレートを clone

```bash
git clone https://github.com/tosh13/llm-wiki-template ~/Projects/llm-wiki-template
```

### 2. セットアップを実行

```bash
bash ~/Projects/llm-wiki-template/scripts/setup.sh
```

スクリプトは以下を行う（途中で確認プロンプトあり）：

- iCloud Drive 内に vault ディレクトリを作成
- `~/llm-wiki` を vault への symlink として作成
- 初期 seed ファイル（概念ページ3件）をコピー
- `schema/CLAUDE.md` を vault に symlink（運用規約）
- `schema/LLM-WIKI.md` を `~/.claude/` に symlink（自動Ingest指示）
- `~/.claude/CLAUDE.md` に `@LLM-WIKI.md` 行を追記
- Web Clipper の設定インポート手順を表示

### 3. Obsidian で開く

Mac の Obsidian で `~/llm-wiki` を vault として開く。
iPhone/iPad の Obsidian でも、同じ vault が iCloud Drive 経由で見える。

### 4. 動作確認

任意のディレクトリで `claude` を起動して、以下を試す：

```
llm-wikiについて教えて
```

→ Claude が `~/llm-wiki/wiki/concepts/llm-wiki-pattern.md` などを読んで答えてくれれば成功。

## 何から読むか

1. `prerequisites.md` — 必要なアカウントとツール
2. `story/design-rationale.md` — なぜこの設計になったかの経緯と設計判断の理由
3. `seed/wiki/concepts/llm-wiki-how-to-use.md` — 日常利用ガイド（Web Clipper・Ingestタイミング・FAQ）
4. `schema/CLAUDE.md` — wiki 運用の規約（参考）

## 継続同期

テンプレートが更新されたら：

```bash
cd ~/Projects/llm-wiki-template
git pull
bash scripts/update.sh
```

`schema/CLAUDE.md` と `schema/LLM-WIKI.md` は symlink 経由で自動反映される。
`seed/` の概念ページは新規追加分のみコピー、手動編集済みのものは保護される。

## ディレクトリ構成

```
llm-wiki-template/
├── README.md                          # このファイル
├── LICENSE                            # MIT License
├── prerequisites.md                   # 前提準備チェックリスト（macOS）
├── prerequisites-windows.md           # 前提準備とセットアップ（Windows）
├── story/
│   └── design-rationale.md            # 経緯と設計判断の理由
├── schema/
│   ├── CLAUDE.md                      # wiki 運用規約（vault に symlink される）
│   └── LLM-WIKI.md                    # ~/.claude/ に symlink される自動Ingest指示
├── seed/                              # 初回コピーのみ（以降は手動編集を尊重）
│   ├── index.md
│   ├── log.md
│   └── wiki/concepts/
│       ├── llm-wiki-pattern.md
│       ├── pkb-folder-structure-patterns.md
│       └── llm-wiki-how-to-use.md
├── prompts/
│   └── handoff-prompt.md              # ChatGPT/Gemini ハンドオフ用プロンプト
├── dotfiles/
│   └── obsidian-web-clipper-settings.json
└── scripts/
    ├── setup.sh                       # 初回セットアップ
    ├── update.sh                      # 継続同期
    └── lib/common.sh
```

## MIGRATION

破壊的変更（major version bump）が入った場合、`update.sh` がここを参照するよう促す。
（現在 v0.1.0 — 破壊的変更はまだなし）

## ライセンス

MIT License. 詳細は [LICENSE](LICENSE) を参照。

## 作者

齋藤俊樹（Toshiki Saito） — 2026年5月作成。
