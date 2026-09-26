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
- `schema/LLM-WIKI.md` を `~/.claude/` に symlink（自動Ingest指示）
- `~/.claude/CLAUDE.md` に `@LLM-WIKI.md` 行を追記
- Web Clipper の設定インポート手順を表示

### 2台目以降は `--wire-only`

```bash
bash ~/Projects/llm-wiki-template/scripts/setup.sh --wire-only
```

**vault は iCloud 上の1つの実体を全端末で共有する。** 2台目以降で vault の中身を書き換えると、その変更は他の端末へ波及する。`.setup-receipt.json` は `template_root` に端末ごとのパスを持つため、端末間で上書きし合う。

かつては `schema/CLAUDE.md` を vault へ symlink していたが、リンク先がその端末にしか無いパスなので他の端末には壊れたリンクとして降りるか消えた。2026-08-17 に廃止し、運用規約はこのリポジトリの `schema/CLAUDE.md` を唯一の正本とした（既に vault へ置かれている端末は、その `CLAUDE.md` を手で削除してよい）。

`--wire-only` はこの端末に必要な配線だけを行う——`~/llm-wiki` の symlink、`~/.claude/LLM-WIKI.md` の symlink、`~/.claude/CLAUDE.md` への `@LLM-WIKI.md` 追記の3つ。vault のディレクトリ・seed・`local-notes.md`・receipt には触れない。

付け忘れても、既に構築済みの vault を見つけた時点で警告が出る。

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
4. `schema/CLAUDE.md` — wiki 運用の規約。Claude がスキーマの正本として読む

## 継続同期

テンプレートが更新されたら：

```bash
cd ~/Projects/llm-wiki-template
git pull
bash scripts/update.sh
```

claude-toolkit を入れている端末では、この節の操作は要らない。`install.py` が毎回テンプレートを pull し、`~/.claude/llm-wiki-template`（clone の実体への別名）と `~/.claude/LLM-WIKI.md` を張り直し、`scripts/vault-migrate.py` で vault を現行の schema に合わせる。

`schema/LLM-WIKI.md` は symlink 経由で自動反映される（Windows はコピーなので `install.py` の再実行で反映される）。`schema/CLAUDE.md` はこのリポジトリが正本なので `git pull` だけで最新になる。
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
│   ├── CLAUDE.md                      # wiki 運用規約（このファイルが正本）
│   └── LLM-WIKI.md                    # ~/.claude/ に symlink される自動Ingest指示
├── seed/                              # 初回コピーのみ（以降は手動編集を尊重）
│   ├── index.md
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
    ├── wiki-index.py                  # 索引を frontmatter から生成
    ├── wiki-health.py                 # vault の健全性点検
    ├── wikilib.py                     # 上2つが使う共通ライブラリ
    └── lib/common.sh
```

## 維持のためのスクリプト

vault が育つと、索引・frontmatter が黙って腐る。人が思い出したときだけ点検する
運用に戻さないための2本（Python 3.9+、依存なし）。

```bash
python3 scripts/wiki-index.py          # 索引を生成（--check でずれの検出だけ）
python3 scripts/wiki-health.py         # 点検。異常が無ければ何も出さない
```

作業ログ（log.md）は 2026-09-24 に廃止した。理由と、既存の log.md の凍結の仕方は
`schema/CLAUDE.md`「変更の記録」にある。

索引（`index.md`・`index/entities-<区分>.md`）は生成物で、正本は各ページの frontmatter
`summary`。索引を手で書くと正本が2本になり、実運用では 354 エントリ中 303 件が
ページ側と食い違った。さらに大きくなった索引は全文を読んでも途中で打ち切られ、
その告知は出ない（450行のうち80行しか返らなかった）。分割と生成はこの2つへの対処。

点検は SessionStart などで毎回走らせる想定（実測 0.1 秒）。vault が無い端末では黙って
終わる。

## MIGRATION

破壊的変更（major version bump）が入った場合、`update.sh` がここを参照するよう促す。
（現在 v0.1.0 — 破壊的変更はまだなし）

2026-09-24 に作業ログ（log.md）を廃止した。以前から使っている vault では、全端末で
`git pull` を済ませてから、vault 直下の log.md を `log/` へ移して凍結する。

```bash
python3 ~/.claude/llm-wiki-template/scripts/vault-migrate.py
```

claude-toolkit を入れている端末では、`install.py` がこれを毎回呼ぶので手で実行する必要は無い。

## ライセンス

MIT License. 詳細は [LICENSE](LICENSE) を参照。

## 作者

齋藤俊樹（Toshiki Saito） — 2026年5月作成。
