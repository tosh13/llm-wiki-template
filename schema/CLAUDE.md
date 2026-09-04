# LLM Wiki — 運用規約 v2.0

## 概要

`~/llm-wiki`（vault）は個人用知識ベース（LLM Wiki）。本ファイルはその運用規約で、実体は llm-wiki-template の `schema/CLAUDE.md` にある。
Karpathyパターンに基づく3層構造。Claude CodeがWikiを維持管理する。
将来的には関心事の全てを対象とする個人KBとして育てていく。

## 3層構造のルール

### Layer 1: sources/ — Raw Sources
- LLMはread-onlyで扱う。絶対に編集しない
- `clippings/`: Obsidian Web Clipperでクリップしたウェブページ
- `handoffs/`: 他AIサービス（ChatGPT, Gemini等）からのハンドオフmdファイル
- `papers/`: 論文・文献の要約・PDF
- `references/`: ~/Projects/ 内の参照ファイルのシンボリック的な記録、GDriveドキュメントへのポインタ

索引（`index.md`・`index/`）は Layer 2 から生成される派生物で、正本ではない。

### Layer 2: wiki/ — LLM-maintained
- Claude Codeが執筆・更新する
- ユーザーはread-onlyとして扱う（訂正は指示ベース）
- ファイル命名: ケバブケース（例: fhir-r4.md, project-strategy.md）
- 各ページのYAMLフロントマターに必須フィールドを付与（下記スキーマ参照）
- 各ページの末尾に「## 参照元」セクションを設け、出典パスを記録
- ページ間参照は `[[ページ名]]` 形式（Obsidianグラフビュー対応）

### Layer 3: CLAUDE.md — Schema
- このファイル。Wiki全体の構造規約とワークフローを定義
- **vault の中には置かない。** かつて vault へ symlink していたが、リンク先が端末ごとに違うのに vault は iCloud 上の1実体を全端末で共有するため壊れた（2026-08-17 に廃止）

## vault のディレクトリ構成

```
wiki/
  concepts/    # 抽象的な知識・方法論・制度の仕組み・技術パターン
  entities/    # 具体的な存在（人物・組織・ツール・法令名）
  synthesis/   # 横断分析・比較・意思決定の記録
index.md       # 生成物。概念・分析の索引と entity 区分の一覧
index/         # 生成物。entities-<区分>.md
log.md         # 直近30日ぶんの作業ログ
log/           # それ以前を月ごとに退避（YYYY-MM.md）
```

**原則**: フォルダは3種のみ。細分類はフロントマターの `type` / `category` / `tags` で行う。
フォルダを追加しない。新しいトピックが来ても既存の3分類に収まる。

### 分類の判断基準

| フォルダ | 判断基準 | 例 |
|---|---|---|
| `concepts/` | 「〜とは何か」「〜の仕組みはどうなっているか」 | 法律の構造、臨床試験のフレームワーク、AI技術パターン |
| `entities/` | 「〜は誰か・何か」（固有名詞で識別できる存在） | 人物、組織、特定の法令名、ツール名 |
| `synthesis/` | 「〜をどう判断するか」「〜を比較すると」（複数要素の統合） | 意思決定の記録、比較分析、プロジェクト戦略の現状 |

## フロントマタースキーマ

全wikiページに必ず付与する：

```yaml
---
type: concept | entity | synthesis
category: person | organization | tool | regulation | method | project | analysis | ...
sensitivity: public | internal | confidential
tags: [grp/<区分>, ...]
aliases: []
sources: []
related_entities: []
related_concepts: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
summary: "1行の要約"
---
```

必須は `type`・`sensitivity`・`summary`・`updated` の4つ。`category` は entity でのみ必須
（person / organization / tool / regulation）。`type` の正本はフォルダで、両者が食い違えば
フォルダを採る。

`summary` は索引の1行になる。索引はこれを詰めて出すので、200字程度までに収める。

entity は `tags` に区分を1つ持つ（`grp/colleague` 等）。この区分が索引のどのファイルに
載るかを決める。区分の一覧と表示名の正本は vault の `index/groups.json`（無ければ
`scripts/wikilib.py` の `DEFAULT_GROUPS`）。区分の中身は環境ごとに違うので、
テンプレート側には持ち込まない。区分が無い entity と、一覧に無い区分は点検が報せる。

```json
{"groups": [{"slug": "colleague", "label": "人物 — 同僚・仕事関係", "category": "person"}]}
```

`title:` は置かない。ページの題は本文の H1 が正本で、frontmatter に写すと二重になる。
別表記は `aliases` に入れる。

### sensitivityの意味

- `public` — 共有可能。法令テキスト、公開議事録、一般的な概念整理
- `internal` — 組織内部向け。組織戦略、プロジェクト状況、業務判断
- `confidential` — 本人のみ。人事評価、個人的な人物評価、人脈戦略

**判断に迷う場合は `confidential` をデフォルトとする**

## 機密情報の取り扱い

このwikiは個人用知識ベースであり、人事判断・人間関係・機微情報を含み得る。機密を別vaultに分離せず単一vaultに含めるのは、同じ人物・案件が複数ページに跨って登場し、分離すると「どちらに書いたか」問題と参照の分断が起きるため。機密を含める代わりに、以下の保護前提を必ず満たすこと。

- `entities/` 内の人物ページは実名可。sensitivity: confidential がデフォルト
- **この vault に git remote を付けない**。vault はローカル専用とし、GitHub等へ push・公開しない。テンプレートリポジトリ（バージョン管理する）と vault（管理しない）は別物である
- 同期は iCloud Drive のみに限定し、**Advanced Data Protection をオンにして E2E 暗号化を有効化**する（サーバー側でも復号できない状態にする）
- 端末を FileVault（ディスク暗号化）と生体認証・パスワードで保護する
- Claude Codeコンテキスト露出は許容（ローカルプロジェクトの参照と同等リスク）
- 将来の部分共有時は `sensitivity: public` のページのみエクスポート対象

## 索引は生成物

索引を手で書かない。`index.md` と `index/entities-<区分>.md` は各ページの frontmatter
`summary` から生成する。ページを追加・削除・改題したら次を実行する。

```bash
python3 ~/Projects/llm-wiki-template/scripts/wiki-index.py
```

索引の記述を直したいときは、索引ではなくページ側の `summary` を直してから生成し直す。
索引に直接書くと正本が2本になり、必ず食い違う。実際に2026-09-04 の点検では 354 エントリ中
303 件がページの summary と食い違い、1エントリが 18,270 文字まで伸びていた。

索引を分割しているのは、1回の Read で全文が返る大きさに収めるため。実測では
26,676 文字で打ち切られ、打ち切りの告知は出ないまま後半が届かなかった（450行の
index.md が 80行しか返らなかった）。

## log.md の更新ルール

作業のたびに log.md の先頭に追記（新しい順）：

```
## YYYY-MM-DD
- 追加: [[ページ名]] — 理由
- 更新: [[ページ名]] — 変更内容
- 移動: [[ページ名]] — 旧パス → 新パス
```

事実の本体はページ側に書き、log.md には何をどう変えたかだけを残す。同じ内容を
ページと log.md の両方に書くと、ページを直したときに log.md が古いまま残る。

log.md は直近30日ぶんだけを持ち、それ以前は月ごとに `log/YYYY-MM.md` へ退避する。

```bash
python3 ~/Projects/llm-wiki-template/scripts/wiki-log-rotate.py --apply
```

## ページの大きさ

1ページは 24,000 文字以内に収める。これを超えると1回の Read で全文が返らず、
後半が黙って届かない。超えたページは主題ごとに分けるか、詳細を `sources/` の
dossier へ移して本体は要約と参照に留める。

## 点検

```bash
python3 ~/Projects/llm-wiki-template/scripts/wiki-health.py
```

索引とページの食い違い、frontmatter の欠落、区分の無い entity、大きすぎるページ、
切れたリンク、同名ページ、ingest されていない sources、log.md の肥大を見る。
異常が無ければ何も出さない。

## Ingestフロー

1. sources/ の新ファイルを読む
2. 既存のwiki/ページと照合（更新が必要なページを特定）
3. 該当ページを更新 or 新規ページを作成
4. 既存ページへの `[[リンク]]` を追加してクロスリファレンスを構築
5. log.md の先頭に追記し、`wiki-index.py` で索引を生成し直す

## Query-to-Page ルール

ユーザーからの質問・分析依頼に回答した際、その回答がwikiページとして価値がある場合：
1. 回答内容をwiki/の適切なカテゴリにページとして保存
2. 既存ページへの[[リンク]]を追加
3. log.md へ追記し、`wiki-index.py` で索引を生成し直す
4. ユーザーに「wikiを更新しました: [[ページ名]]」と報告

保存の判断基準：
- 事実の整理・比較分析を含む回答 → 保存
- 単純な手順実行の報告 → 保存しない
- 意思決定とその理由 → wiki/synthesis/ に保存

## 人物エンティティページのテンプレート

```markdown
---
type: entity
category: person
sensitivity: confidential
tags: [grp/<区分>]
aliases: []
sources: []
related_entities: []
related_concepts: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
summary: "所属・役割の1行要約"
---
# [氏名]

所属:
役割:
関係性: [[関連組織]]

## 人物メモ
（性格、判断傾向、重要な背景情報など）

## 接触記録
- YYYY-MM-DD: 内容の要約

## 参照元
```

## Living Source 参照パターン

GDrive上の生きたドキュメントは sources/references/ にポインタを置く：
- ファイル名: `gdrive-[説明]-pointer.md`
- 内容: GDrive file ID、ingest日時、ドキュメントの概要
- 定期的に再ingestして鮮度を保つ

## 個人ごとの追加指示

vault 直下に `local-notes.md` があれば読む（Ingest 優先度・環境固有の指示）。本ファイルは vault の外（llm-wiki-template）にあるため、`@local-notes.md` のような相対 import では解決されない。
