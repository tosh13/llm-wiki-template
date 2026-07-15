# この運用に至った設計思想

> このテンプレートが「Claude が自動で知識を整理する仕組み」に辿り着くまでの経緯と、各設計判断の理由を時系列で残す。
> 手順を真似るだけなら README で足りるが、「なぜそうなっているのか」が分かると、自分の判断で設計を改造できる。

---

## メンテナンスコストという本質的課題

Evernote、Notion、純正メモ、紙のノート、テキストファイル——知識を貯める試みはたいてい半年で破綻する。理由はいつも同じで、**メンテナンスコスト**だ。

新しい情報を得るたびに、関連する過去のメモを探し、リンクを貼り、用語の表記を揃え、矛盾があれば書き直す——これを毎日続けられる人間はいない。だから個人のメモは「過去の自分が書いた断片の墓場」になる。

1945年、ヴァネヴァー・ブッシュは「Memex」[^memex] を構想した。連想リンクで全知識をつなぐ個人用知識マシンで、インターネットの原型と言われる。だが当時から問題はずっと「メンテを誰がやるか」だった。ブッシュには答えが出せなかった。LLM が答えを出した。

[^memex]: Vannevar Bush, "As We May Think", The Atlantic, 1945年7月号。

---

## Karpathyパターン

2026年5月4日、Andrej Karpathy[^karpathy] が GitHub Gist に "LLM Wiki" と題する短文を投稿した。要約するとこうだ。

> RAG[^rag] はクエリのたびに文書断片を検索する。それは検索であって、知識の蓄積ではない。
> 代わりに、LLM に **wiki を執筆・維持** させる。新しいソースを与えるたびに、関連ページを書き換え、リンクを張り直し、矛盾を解消する作業を LLM に任せる。
> 人間は「ソースをキュレートする」「良い質問をする」「意味を考える」だけ。要約・整理・ブックキーピングは LLM の仕事。

これが正解だった。LLM は退屈しない、忘れない、15ファイルを一気に編集できる。**人間が wiki を諦める理由（メンテ負担）が、ちょうど LLM が得意な領域**だった。

[^karpathy]: Andrej Karpathy。元OpenAI、元Tesla AI 部門ディレクター。LLM コミュニティで影響力のある研究者。
[^rag]: Retrieval-Augmented Generation（検索拡張生成）。文書をベクトル化し、質問に近い断片を LLM に食わせる手法。

---

## 初期構成の問題点

最初の構成は、業務で扱うものを素直に並べた6フォルダだった。

```
wiki/
  projects/        # プロジェクトごと
  stakeholders/    # 関わる人物
  legal/           # 法令・規制
  decisions/       # 意思決定の記録
  organizations/   # 組織情報
  concepts/        # 抽象的な概念
```

すぐに「この論点まとめは projects なのか legal なのか」と迷い始めた。**どちらでも良い**気がして決まらない。

翌朝に気づいたのは、`projects/` フォルダがある時点で **wiki の寿命がプロジェクトのライフサイクルに縛られる** ということだ。プロジェクトは終わる。戦略は数年で一変し、関わる人物も変わる。そのとき配下の全ページを誰がリネームするのか——結局「人間がメンテする」に戻ってしまう。**フォルダ名にプロジェクト概念を入れた瞬間、Karpathy パターンの「永続的に複利成長する wiki」という思想と矛盾する**。

---

## 5実装の比較

同じことをやっている実装を世界中から探し、5例を比較した。

| 実装 | フォルダ構成 |
|---|---|
| Karpathy 原典 | 抽象的（ユーザーが設計） |
| NicholasSpisak/second-brain | sources/ entities/ concepts/ synthesis/ |
| Ar9av/obsidian-wiki | _meta/ Global/ Concepts/ Patterns/ Tools/ Projects/ |
| kfchou/wiki-skills | pages/（完全フラット、フォルダゼロ） |
| kennyg's Obsidian Setup | entities/ concepts/ synthesis/ |

並べると、**深いフォルダ構成は全員が試して全員が放棄している**ことが分かった。そして 4/5 の実装で `concepts` `entities` `synthesis` の3種（名前は微妙に違うが意味は同じ）が登場する。偶然ではない。**人間が長期間維持できる大分類は3つが限界**なのだろう。フォルダを増やすほど「どこに入れるか迷う時間」が増え、メンテが破綻する。

---

## frontmatterによる分類

そこで3フォルダに作り変えた。

```
wiki/
  concepts/    # 抽象的な知識（〜とは何か）
  entities/    # 具体的な存在（人・組織・ツール・特定の法令）
  synthesis/   # 横断分析（〜をどう判断するか・比較・意思決定）
```

細かい分類はフォルダではなく、各 `.md` の先頭の **frontmatter**[^frontmatter] で行う。

```yaml
---
type: entity
category: person
sensitivity: confidential
tags: [example]
---
```

この方式の良さは **フォルダ移動が不要**になること。カテゴリを変えたければ frontmatter を1行書き換えるだけで、`[[リンク]]` は壊れない。旧6フォルダは concepts / entities / synthesis の3種に吸収された。この3フォルダ構成が現行版であり、以後変えていない。

[^frontmatter]: ファイル冒頭の `---` で囲まれた YAML 領域。Obsidian や Hugo などがメタデータとして扱う。

---

## ハンドオフプロンプトの設計

ChatGPT や Gemini で得た成果物を wiki に取り込む導線も、3世代の試行錯誤で安定させた。

- **v1（素朴な指示）**: 「会話を踏まえて md をアウトプットして」→ 要約されすぎ、詳細に議論した部分が省略される。「まとめる＝省略」と受け取られる。
- **v2（2ステップ）**: 「まず全文を md にダンプ。次に会話を別 md でまとめて」→ 全文ダンプは効くが、出力ファイル名のメタ情報がコピー時に消える。
- **v3（YAML frontmatter）**: ファイル名と sensitivity を md ブロック内側の frontmatter に埋め込む→ そのまま `.md` 保存すればファイル名情報が残り、後から Claude が `filename:` を取り出せる。

これが `prompts/handoff-prompt.md`。**「まとめろ」と「省略するな」を両立させるのは難しい**という学びが形になっている。

---

## 保管場所と機密管理

**iCloud Drive を選んだ理由**:

- iPhone / iPad の Obsidian で同じ vault を見たい
- git だと「commit → push → pull」がモバイルで現実的でない
- iCloud Drive は Apple の E2E 暗号化[^e2e]（Advanced Data Protection）があり、利便性と現実的なリスクのバランスが取れる
- 母艦の Mac が物理的に施錠された場所にあり、生体認証で守られている

**機密情報を別 vault に分けなかった理由**:

- 2つに分けると「どっちに書いたか」問題が生じる
- 人物の評価メモと方法論の整理は密接にリンクする（同じ人物が複数ページに登場する）
- だから単一 vault に全部入れ、各ページの frontmatter に `sensitivity: public | internal | confidential` を付ける

**機密を含めるための前提条件**（重要）: 単一 vault に機微情報を入れる代わりに、次を必ず満たす。①**vault に git remote を付けない**（ローカル専用。GitHub 等へ push・公開しない。バージョン管理するのはテンプレートリポジトリだけで、vault 本体は管理対象外）。②同期は iCloud Drive のみに限定し **Advanced Data Protection をオンにして E2E を有効化**する。③端末を FileVault と生体認証で保護する。将来 wiki の一部を共有したくなったら `sensitivity: public` のページだけをエクスポートすればよい。

[^e2e]: End-to-End Encryption。サーバー（Apple）でも復号できない暗号化。iCloud Drive は Advanced Data Protection をオンにすると有効になる。

---

## 自動Ingestとセッション終了時の整理

この運用の核心は、**ユーザーは wiki のメンテを意識しない** ように設計されている点にある。

普通の wiki 運用なら「今日クリップしたから整理しよう」と人間が能動的に動く必要がある。それが続かないから世界中の wiki が墓場になる。この設計では、Claude Code が **全プロジェクトのセッション中に** 自律的に「これは wiki に蓄積すべき情報か」を判断し、必要なら sources/ や wiki/ に書き込む。仕組みはこうだ。

1. `schema/LLM-WIKI.md` に、Ingest 対象の判断基準・Query フロー・コンテキスト効率ルールが書いてある
2. このファイルは `setup.sh` によって `~/.claude/LLM-WIKI.md` に **symlink** される
3. `setup.sh` はさらに `~/.claude/CLAUDE.md`（Claude Code のグローバル設定）末尾に `@LLM-WIKI.md` を追記する。これにより **Claude Code 起動のたびに LLM-WIKI.md の中身がグローバルに読み込まれる**[^import]

結果、どのプロジェクトで `claude` を起動しても、Claude は「今日この情報を扱ったから [[xxx]] に追加すべき」「この質問は [[yyy]] に答えがある」「この回答は分析を含むから wiki ページとして保存」を **勝手に判断** して動く。

Ingest はセッションの途中だけでなく **終了時にも走る**。終了の合図を受けると、Claude はそのセッションで扱った人物や話題の新事実を該当ページに追記し、log.md に変更を記録し、index.md を実体と揃えてから終える。途中で取りこぼした更新も終了時にまとめて拾われる。この終了時処理は `schema/LLM-WIKI.md` の「セッション終了時」に定義してあり、Claude Code の終了ルーチン（SESSION-END）を別に持つ場合はその一部として組み込む。

判断ロジックを更新したら（例：新しい Ingest カテゴリを追加）、各 vault では `git pull && bash scripts/update.sh` を一度走らせるだけで次回起動から新ルールが効く。**symlink 一本で運用が同期する**——これがテンプレートリポジトリ方式の旨味である。

[^import]: Claude Code は `~/.claude/CLAUDE.md` 内で `@filename.md` と書くとその内容を import する。複数ファイルに分けて管理できる。

---

## 継続改善

この運用は完成形ではない。テンプレートが更新されたら `git pull && bash scripts/update.sh` で追従できる。改善案があれば Pull Request を送ってほしい。設計の背後にある比較研究は [[llm-wiki-pattern]]・[[pkb-folder-structure-patterns]]（seed の概念ページ）を参照。
