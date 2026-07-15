# LLM Wiki — 運用規約 v2.0

## 概要

このディレクトリは個人用知識ベース（LLM Wiki）。
Karpathyパターンに基づく3層構造。Claude CodeがWikiを維持管理する。
将来的には関心事の全てを対象とする個人KBとして育てていく。

## 3層構造のルール

### Layer 1: sources/（Raw Sources）
- LLMはread-onlyで扱う。絶対に編集しない
- `clippings/`: Obsidian Web Clipperでクリップしたウェブページ
- `handoffs/`: 他AIサービス（ChatGPT, Gemini等）からのハンドオフmdファイル
- `papers/`: 論文・文献の要約・PDF
- `references/`: ~/Projects/ 内の参照ファイルのシンボリック的な記録、GDriveドキュメントへのポインタ

### Layer 2: wiki/（LLM-maintained）
- Claude Codeが執筆・更新する
- ユーザーはread-onlyとして扱う（訂正は指示ベース）
- ファイル命名: ケバブケース（例: fhir-r4.md, project-strategy.md）
- 各ページのYAMLフロントマターに必須フィールドを付与（下記スキーマ参照）
- 各ページの末尾に「## 参照元」セクションを設け、出典パスを記録
- ページ間参照は `[[ページ名]]` 形式（Obsidianグラフビュー対応）

### Layer 3: CLAUDE.md（Schema）
- このファイル。Wiki全体の構造規約とワークフローを定義

## wiki/ のディレクトリ構成

```
wiki/
  concepts/    # 抽象的な知識・方法論・制度の仕組み・技術パターン
  entities/    # 具体的な存在（人物・組織・ツール・法令名）
  synthesis/   # 横断分析・比較・意思決定の記録
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
tags: []
aliases: []
sources: []
related_entities: []
related_concepts: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
summary: "1行の要約（index.md・log.mdスキャン用）"
---
```

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

## index.md の更新ルール

Wikiページを新規作成・削除するたびに index.md を更新すること：
- カテゴリ別にリスト化
- 各エントリは `- [[ページ名]] — summary フィールドの内容` の形式

## log.md の更新ルール

作業のたびに log.md の先頭に追記（新しい順）：

```
## YYYY-MM-DD
- 追加: [[ページ名]] — 理由
- 更新: [[ページ名]] — 変更内容
- 移動: [[ページ名]] — 旧パス → 新パス
```

## Ingestフロー（新しいsourcesファイルを取り込む際）

1. sources/ の新ファイルを読む
2. 既存のwiki/ページと照合（更新が必要なページを特定）
3. 該当ページを更新 or 新規ページを作成
4. 既存ページへの `[[リンク]]` を追加してクロスリファレンスを構築
5. index.md と log.md を更新

## Query-to-Page ルール

ユーザーからの質問・分析依頼に回答した際、その回答がwikiページとして価値がある場合：
1. 回答内容をwiki/の適切なカテゴリにページとして保存
2. 既存ページへの[[リンク]]を追加
3. index.md, log.md を更新
4. ユーザーに「wikiを更新しました: [[ページ名]]」と報告

保存の判断基準：
- 事実の整理・比較分析を含む回答 → 保存
- 単純な手順実行の報告 → 保存しない
- 意思決定とその理由 → wiki/synthesis/ に保存

## エンティティページテンプレート（人物）

```markdown
---
type: entity
category: person
sensitivity: confidential
tags: []
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

@local-notes.md
