---
type: concept
category: method
sensitivity: public
tags:
  - how-to
  - llm-wiki
  - web-clipper
  - workflow
summary: "llm-wikiの日常利用ガイド。クリッピングからwikiページ化までの流れを具体例で説明。"
created: 2026-05-05
updated: 2026-05-05
---

# llm-wiki 利用ガイド

## このwikiとは

調べたこと・考えたこと・会議で得た情報を、AIが自動で整理・蓄積する個人用知識ベース。
ユーザーは「保存したいものを放り込む」だけ。整理はClaude Codeが担当する。
使うほど知識が積み重なり、次の作業がより速く・深くなる。

---

## 基本フロー

```
あなたが行う操作                  Claudeが自動で行う
─────────────────────────────────────────────────────
Web記事をクリップ ──→ sources/clippings/  ─┐
ChatGPTの出力を保存 → sources/handoffs/   ─┼→ wiki/ にページとして整理
論文・文献を追加  ──→ sources/papers/     ─┘
                                               ↓
                                         Obsidianで閲覧
                                         （全デバイス対応）
```

`sources/` は生素材の置き場。`wiki/` がClaudeの清書済みノート。

---

## Web Clipperで記事を保存する

### 操作手順

1. ChromeでクリップしたいWebページを開く
2. ツールバーのObsidian Web Clipperアイコン（紫色）をクリック
3. テンプレート「llm-wiki source」が選択されていることを確認
4. 「Add to Obsidian」ボタンをクリック
5. 完了（Obsidianが起動するが、そのまま閉じてよい）

### 保存後のファイル

```
sources/clippings/20260505-OAuth 2.0 認可フロー.md
```

ファイルには以下のメタデータが自動付与される：

```yaml
type: source-summary
sensitivity: public
tags: [clipping]
source: https://datatracker.ietf.org/doc/html/rfc6749
author:
created: 2026-05-05
```

### 注意点

- **Obsidianは常駐させておく**のが推奨（バックグラウンド起動でOK）。起動していないとクリップのたびに前面に出てくる
- デフォルトの `sensitivity: public` は**公開ページ用**。機密性のある社内文書などをクリップした場合は、保存後にObsidianでファイルを開き `sensitivity: confidential` に書き換える
- 重複してクリップしても問題ない（ファイル名末尾に ` 1` が付く。不要なら削除）

---

## wikiページになるタイミング

`sources/clippings/` に保存しただけでは `wiki/` には現れない。
以下の3パターンでIngest（整理・昇格）が行われる。

### パターンA：関連する話題をClaudeと話したとき（自動）

Claude Codeで作業中に、クリッピングと関連するトピックが出ると自動でIngestされる。

**例：**

> 「OAuth 2.0 の認可フローを整理したい」

→ Claudeが `sources/clippings/` に OAuth 2.0 のクリッピングがあることを検知
→ `wiki/concepts/oauth2.md` を自動作成
→「wikiを更新しました: [[oauth2]]」と報告

### パターンB：まとめて整理を依頼する

```
sources/clippings/ に溜まったクリッピングをwikiに整理して
```

と指示すれば一括処理される。

### パターンC：溜め置きでOK（推奨）

**クリップは溜まったままで問題ない。**
「今日クリップしたから今日整理しなければ」という義務はない。
関連する作業が発生したときに初めて整理されるのが自然な流れ。

> 例：1ヶ月後にそのテーマのプロジェクトが本格始動したタイミングで、過去のクリッピングがまとめてwiki化される

---

## ChatGPT / Gemini の成果物を引き継ぐ

他のAIサービスで得た分析・要約を、llm-wikiに取り込む手順：

1. テンプレートリポジトリの `prompts/handoff-prompt.md` をスレッド末尾に貼り付けて実行
2. 出力された内容を `.md` ファイルとして `~/llm-wiki/sources/handoffs/` に保存
   - ファイル名は出力冒頭のYAML frontmatter `filename:` の値をそのまま使う
3. 以上。次のClaude Codeセッションで自動的にIngestされる

---

## Obsidianで閲覧する

### デスクトップ（MacBook / Mac mini）

- Obsidian起動 → Vault: `llm-wiki` を開く
- **グラフビュー**（左サイドバー）でページ間のつながりを視覚化できる
- **検索**（Cmd+F または左サイドバー）でキーワード検索
- **Backlinks**で「このページを参照しているページ」を確認

### iPhone / iPad

- Obsidianアプリ → iCloud Driveのvaultとして同じ `llm-wiki` を開く
- MacBookでの変更は数秒〜数分でiCloudを通じて同期される

---

## sensitivityタグの使い分け

全wikiページに必ず付いている `sensitivity` フィールドで、3段階に分類する。

| タグ | 意味 | 具体例 |
|---|---|---|
| `public` | 共有可能 | 法令テキスト、学術論文の要約、一般的な技術解説 |
| `internal` | 組織内向け | プロジェクト戦略、会議の意思決定記録 |
| `confidential` | 本人のみ | 人事評価、個人的な人物メモ、給与・予算情報 |

Claudeがページ作成時に自動判定して付与する。判断が難しい場合は `confidential` がデフォルト。

---

## よくある質問

**Q: クリップしたのにwikiに出てこない**
A: まだIngestされていないだけ。`sources/clippings/` に保存されている。関連する話題でClaudeと話すか、「clippingsを整理して」と依頼すればwikiページ化される。

**Q: 同じページを2回クリップしてしまった**
A: `sources/clippings/` に `ファイル名 1.md` という重複ファイルができる。Obsidianで開いて不要な方を削除すればOK。

**Q: 間違った内容がwikiページになった**
A: wikiページはClaudeが書くが、訂正はいつでもできる。「[[ページ名]]の〇〇を修正して」と指示すれば更新される。

**Q: Obsidianがインストールされていないデバイスでも見られるか**
A: iCloud Drive内のファイルなので、iCloudドライブのWebサイト（icloud.com）からもMarkdownファイルとして閲覧可能。ただし整形されない。

**Q: 機密情報が誤って `public` で保存された**
A: Obsidianでそのファイルを開き、フロントマターの `sensitivity: public` を `sensitivity: confidential` に書き換える。Claudeに「このページのsensitivityをconfidentialに変えて」と指示してもよい。

---

## 参照元

- [[llm-wiki-pattern]] — このwikiの設計思想（Karpathyパターン）
- [[pkb-folder-structure-patterns]] — フォルダ構成の比較研究
- テンプレートリポジトリの `story/design-rationale.md` — 現運用に至った経緯と設計判断の理由
- テンプレートリポジトリの `README.md` — 初期セットアップ手順
