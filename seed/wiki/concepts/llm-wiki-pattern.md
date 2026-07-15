---
type: concept
category: method
sensitivity: public
tags: [llm-wiki, methodology, karpathy, knowledge-management]
aliases: [Karpathyパターン, LLM Wiki]
sources: [karpathy-llm-wiki-gist.md, developersio-llm-wiki-article.md]
related_entities: []
related_concepts: [pkb-folder-structure-patterns]
created: 2026-05-05
updated: 2026-05-05
summary: "LLMが維持管理する個人用知識ベースの設計パターン。RAGと異なり複利で成長するwikiを構築する。"
---

# LLM Wikiパターン

Andrej Karpathyが提唱する、LLMを使った個人用知識ベースの構築・維持パターン。
RAGとは根本的に異なる「コンパイル型」知識管理の考え方。

## コアコンセプト

RAGはクエリのたびに文書断片を検索して回答を再生成する。知識は蓄積されない。

LLM Wikiはこれと根本的に異なる：
> "The LLM incrementally builds and maintains a persistent wiki—a structured, interlinked collection of markdown files that sits between you and the raw sources."

**Wikiは複利で成長するアーティファクト**。新しいソースや質問のたびに豊かになる。

役割分担：
- **人間**: ソースのキュレーション、良い質問をする、意味を考える
- **LLM**: 要約・クロスリファレンス・整理・ブックキーピング（＝それ以外の全て）

## 3層アーキテクチャ

| 層 | 内容 | 権限 |
|---|---|---|
| Layer 1: Raw Sources | 不変の原資料（記事・論文・PDF・メモ） | LLMはread-only |
| Layer 2: Wiki | LLM生成のMarkdownファイル群 | LLMが執筆・更新、人間はread-only |
| Layer 3: Schema (CLAUDE.md) | wikiの構造規約・ワークフロー定義 | 人間とLLMが協同で進化させる |

## 3オペレーション

### Ingest（取り込み）
新しいソースをRaw Sourcesに追加し、LLMがwikiに統合する。
1ソースで10〜15ページに影響しうる。ソース1件ずつ、ユーザーが関与しながら行うのが推奨。

### Query（参照）
wikiに対して質問する。LLMがindex.mdを読み、関連ページを参照して回答。
**重要**: 良い回答はwikiページとして保存し直す（= Queryも知識を複利成長させる）。

### Lint（整合性チェック）
定期的にwikiの健全性を確認：
- ページ間の矛盾
- 新しいソースで陳腐化した主張
- インバウンドリンクのない孤立ページ
- 重要な概念なのに専用ページがないもの

## index.md と log.md

**index.md**: コンテンツ目録。カテゴリ別にページをリスト。LLMはクエリ時にまずここを読む。
**log.md**: 時系列記録。何をいつ行ったかの追記専用ログ。

## なぜ機能するか

> "Humans abandon wikis because maintenance burden grows faster than value. LLMs don't get bored, don't forget cross-reference updates, and can touch 15 files in one pass."

メンテナンスコストがゼロに近づくため、wikiが放棄されず育ち続ける。

## この実装がKarpathy原典・他実装と異なる点

Karpathy原典と公開されている他実装（second-brain, obsidian-wiki 等）を比較したうえで、この実装は4つの点で質的に踏み込んでいる。

- **フォルダを3種に固定しfrontmatterへ寄せた**: 原典はフォルダ構成をユーザー任せの抽象に留める。他実装も試行の末に concepts / entities / synthesis の3種へ収束している。この実装はその3フォルダを採用したうえで、細分類を一切フォルダに持たせず frontmatter（type / category / sensitivity / tags）に寄せ、**フォルダ移動ゼロ**を徹底する。カテゴリ変更は1行の書き換えで済み、`[[リンク]]` が壊れない。
- **機密を含められる単一ローカルvaultにした**: 多くの実装は公開・共有を前提とし機密モデルを持たない。この実装は sensitivity タグ＋git remoteを持たないローカル専用vault＋iCloud E2E により、人事評価・人脈といった機微情報まで同一KBに集約できる（→「機密情報の取り扱い」）。
- **メンテを完全自動化した**: 原典は Ingest / Query / Lint を人間が明示的に回す。この実装はスキーマを `~/.claude/CLAUDE.md` へ symlink＋`@import` することで、**どのプロジェクトでClaudeを起動しても**セッション中の自動Ingest・セッション終了時の整理までが人間の操作なしに走る。ユーザーはwikiのメンテを意識しない。
- **他AIの成果物を無損失に取り込む導線を用意した**: ChatGPT / Gemini 等の出力を、frontmatterで囲んだハンドオフプロンプト（`prompts/handoff-prompt.md`）経由で要約損失なく sources/ に落とし、次セッションで自動Ingestさせる。

## Vannevar Bushのメメックスとの関係

1945年にVannevar Bushが提唱した「Memex」（個人用の連想リンク付き知識ストア）のビジョンに精神的に近い。
Bushが解決できなかったのはメンテナンスの問題。それをLLMが解決する。

## このwikiでの実装

→ [[pkb-folder-structure-patterns]] — 長期安定するフォルダ構成パターンの比較研究
→ [[llm-wiki-how-to-use]] — 日常利用ガイド（Web Clipper・Ingestタイミング・FAQ）

## 参照元

- Karpathy原典Gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- DevelopersIO解説記事: https://dev.classmethod.jp/articles/karpathy-llm-wiki/
