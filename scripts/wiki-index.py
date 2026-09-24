#!/usr/bin/env python3
"""索引をページの frontmatter から生成する。

索引を手で書くと、ページ側の summary と索引の本文という正本が2本になる。実際に
2026-09-04 時点で 354 エントリ中 303 件がページの summary と食い違い、索引の1行が
最長 18,270 文字まで伸びて、index.md 全文を読んでも 450行中 80行しか返らない状態に
なっていた（打ち切りの告知は出ない）。索引は生成物にして、直す先をページ側だけにする。

  index.md                  目次・Concepts・Synthesis・entity 区分の一覧
  index/entities-<区分>.md   その区分の entity

entity を1ファイルに並べると打ち切りに届く（281件で 23,396 文字。実測の打ち切りは
26,676 文字で、entity は4か月で280件増えている）。区分ごとに分けると、1区分が
数百件になるまで打ち切りに触れない。区分ラベルの正本は wikilib.GROUPS で、ページ側は
tags に `grp/<区分>` を持つだけでよい。
"""

from __future__ import annotations

import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wikilib as W

CONCEPT_LIMIT = 110
ENTITY_LIMIT = 60

HEADER = (
    "> このファイルは scripts/wiki-index.py が生成する。手で編集しても次の生成で消える。\n"
    "> 各行はページの frontmatter `summary` から作るので、直すときはページ側を直す。\n"
)


def line(page: W.Page, limit: int, with_title: bool) -> str:
    summary = W.value_summary(page)
    title = page.title
    prefix = "— "
    if with_title and title and W.norm(title) not in W.norm(summary):
        prefix = f"{title} — "
    return f"- [[{page.slug}]] {prefix}{W.trim(summary, limit)}".rstrip()


def build(vault: str) -> dict[str, str]:
    pages = W.load(vault)
    by_type: dict[str, list[W.Page]] = {"concept": [], "entity": [], "synthesis": []}
    for p in pages:
        by_type.setdefault(p.type, []).append(p)
    today = datetime.date.today().isoformat()
    counts = {k: len(v) for k, v in by_type.items()}

    # --- index.md ---
    out = ["# LLM Wiki Index", ""]
    out.append(HEADER.rstrip())
    out.append(f"> 生成 {today}／ページ {len(pages)}件"
               f"（concept {counts.get('concept', 0)}・entity {counts.get('entity', 0)}"
               f"・synthesis {counts.get('synthesis', 0)}）")
    out.append("")
    out.append("## Concepts（抽象的な知識・方法論・制度の仕組み）")
    out.append("")
    for p in sorted(by_type.get("concept", []), key=lambda x: x.slug):
        out.append(line(p, CONCEPT_LIMIT, with_title=False))
    out.append("")
    out.append("## Synthesis（横断分析・比較・意思決定の記録）")
    out.append("")
    for p in sorted(by_type.get("synthesis", []), key=lambda x: x.slug):
        out.append(line(p, CONCEPT_LIMIT, with_title=False))
    out.append("")
    index_md = "\n".join(out)

    # --- 区分ごとの entity 索引 ---
    ents = by_type.get("entity", [])
    grouped: dict[str, list[W.Page]] = {}
    for p in ents:
        for g in (p.groups or ["unfiled"]):
            grouped.setdefault(g, []).append(p)

    order = [g for g, _, _ in W.GROUPS if g in grouped]
    order += sorted(g for g in grouped if g not in {x for x, _, _ in W.GROUPS})

    files: dict[str, str] = {}
    out.append("## Entities（人物・組織・法令・ツール）")
    out.append("")
    for g in order:
        label = W.GROUP_LABEL.get(g, f"未分類（{g}）")
        out.append(f"- [[entities-{g}]] {label} — {len(grouped[g])}件")
    out.append("")
    index_md = "\n".join(out)

    for g in order:
        label = W.GROUP_LABEL.get(g, f"未分類（{g}）")
        body = [f"# {label}", ""]
        body.append(HEADER.rstrip())
        body.append(f"> 生成 {today}／{len(grouped[g])}件。"
                    f"このページに載るのは tags に `grp/{g}` を持つ entity。")
        body.append("> 目次: [[index]]")
        body.append("")
        for p in sorted(grouped[g], key=lambda x: x.slug):
            body.append(line(p, ENTITY_LIMIT, with_title=True))
        body.append("")
        files[os.path.join("index", f"entities-{g}.md")] = "\n".join(body)

    files["index.md"] = index_md
    return files


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=W.vault_root())
    ap.add_argument("--check", action="store_true",
                    help="生成結果と現物を比べるだけ。ずれていれば終了コード1")
    args = ap.parse_args()

    files = build(args.vault)
    stale = []
    os.makedirs(os.path.join(args.vault, "index"), exist_ok=True)
    # 区分が消えたときに古い索引を残さない（実体と索引を一致させる）
    keep = {os.path.basename(n) for n in files if n.startswith("index" + os.sep)}
    for f in sorted(os.listdir(os.path.join(args.vault, "index"))):
        if f.endswith(".md") and f not in keep:
            if args.check:
                stale.append(f"index/{f}（区分が無くなったのに残っている）")
            else:
                os.remove(os.path.join(args.vault, "index", f))
                print(f"index/{f}: 削除（区分なし）")
    for name, text in sorted(files.items()):
        path = os.path.join(args.vault, name)
        cur = ""
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                cur = fh.read()
        n = len(text)
        over = "  ← 1回の Read に収まらない" if n > W.READ_CAP_CHARS else ""
        if _body(cur) == _body(text):
            continue  # 中身が同じなら書かない。iCloud が全端末へ配り直すのを避ける
        if args.check:
            stale.append(name)
            continue
        # 一時ファイルに書いてから置き換える。途中で止まっても半端な索引を残さない
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
        print(f"{name}: {n:,} 文字 / {text.count(chr(10)) + 1} 行{over}")

    if args.check:
        if stale:
            print("索引がページと食い違っている（生成し直す）: " + "・".join(stale))
            return 1
        print("索引はページと一致")
    return 0


def _body(text: str) -> str:
    """生成日の行だけは比較から外す。日付で毎日ずれると検知が意味を失う。"""
    return "\n".join(l for l in text.splitlines() if not l.startswith("> 生成 "))


if __name__ == "__main__":
    sys.exit(main())
