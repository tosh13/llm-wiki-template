---
type: concept
category: method
sensitivity: public
tags: [llm-wiki, knowledge-management, obsidian, folder-structure]
aliases: [PKBフォルダ構成, 個人KB構造パターン]
sources: []
related_entities: []
related_concepts: [llm-wiki-pattern]
created: 2026-05-05
updated: 2026-05-05
summary: "長期安定するPKBフォルダ構成の比較研究。5実装例の分析から3フォルダ+フロントマター方式が最適と判明。"
---

# PKBフォルダ構成パターン

個人用知識ベース（PKB / Personal Knowledge Base）の長期安定するフォルダ構成に関する比較研究。
2026-05-05に5つの実装例を調査し、このwikiのv2.0構成設計に反映した。

## 調査の背景

初期設計（v1.0）では `projects/`, `stakeholders/`, `legal/`, `decisions/`, `organizations/`, `concepts/` の6フォルダを使用していた。
しかしプロジェクト名フォルダはプロジェクトのライフサイクルに依存し、長期的に陳腐化するという問題があった。

## 比較した5つの実装例

| 実装 | wiki/配下の構成 | 特徴 |
|---|---|---|
| Karpathy原典 | 抽象的（ユーザーが設計） | 「設計はユーザーが行う」という思想 |
| NicholasSpisak/second-brain | sources/, entities/, concepts/, synthesis/ | 多エージェント対応、lintスキル付き |
| Ar9av/obsidian-wiki | _meta/, Global/Patterns/Tools/Concepts/, Projects/ | 最も詳細。provenanceタグまで管理 |
| kfchou/wiki-skills | pages/（完全フラット） | フォルダゼロ、typeフロントマターのみ |
| kennyg's Obsidian Setup | entities/, concepts/, synthesis/ | confidence/source_countスコアリング |

## 共通知見

### 1. フォルダ深度: 浅いほど長続きする

全実装が最大2〜3階層。深いフォルダ構成は全員が試みて全員が放棄している。

### 2. 4種のほぼ普遍的なページタイプ

| タイプ | 採用数 | 内容 |
|---|---|---|
| concepts | 5/5 | 抽象的なアイデア・パターン・方法論 |
| entities | 4/5 | 具体的な存在（人・組織・ツール） |
| sources | 5/5 | 取り込んだ素材の要約 |
| synthesis | 4/5 | 横断分析・比較・意思決定 |

### 3. 分類の主手段: フロントマター > フォルダ

フォルダによる細分類（projects/, legal/, stakeholders/...）は分類迷子を生み、将来の再構成コストが高い。
`type`, `category`, `tags` フィールドでの分類はフォルダ移動なしで再分類できる。

### 4. 長期安定する理由

- リンクとタグはフォルダ階層よりスケールする
- LLMはindex.mdを読む → フォルダ深度は関係ない
- フラット構造 = grep可能・git diffable・将来のツール変更に強い

## 発展的なフロントマターフィールド（採用を検討）

| フィールド | 意味 | 採用元 |
|---|---|---|
| `confidence` | 主張の確からしさ（high/medium/low） | kennyg |
| `provenance` | 根拠の種類（extracted/inferred/ambiguous） | Ar9av |
| `summary` | 1行要約（index.mdスキャン用） | 複数 |
| `source_count` | 裏付けソース数 | kennyg |

このwikiではv2.0から `summary` を採用。`confidence`/`provenance` は将来検討。

## このwikiのv2.0構成

上記分析に基づき、6フォルダ → 3フォルダに集約：

```
wiki/
  concepts/    # 抽象的な知識・方法論・制度の仕組み
  entities/    # 具体的な存在（人物・組織・ツール・法令名）
  synthesis/   # 横断分析・比較・意思決定の記録
```

旧フォルダとの対応：
- `projects/` → synthesis/（プロジェクト横断分析）
- `stakeholders/` → entities/（人物はentityの一種、category: person）
- `legal/` → concepts/（法制度）+ entities/（個別法令名）
- `decisions/` → synthesis/（意思決定は複数要素の統合）
- `organizations/` → entities/（category: organization）

## 参照元

- Karpathy原典: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- NicholasSpisak/second-brain: GitHub
- Ar9av/obsidian-wiki: GitHub
- kfchou/wiki-skills: GitHub
- テンプレートリポジトリの `story/how-this-was-built.md` — v1.0→v2.0の設計遷移
