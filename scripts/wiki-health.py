#!/usr/bin/env python3
"""llm-wiki vault の健全性点検。

2026-09-04 のレビューで見つかった劣化は、どれも「静かに起きて誰も見ていない」形
だった。索引がページと食い違う（354件中303件）、frontmatter が3世代混在する、
索引が打ち切られても告知が出ない、sources に ingest されないまま残る。人が思い出した
ときだけ点検する運用に戻すと同じ形で腐るので、機械が毎回見る。

drift-check.py（SessionStart）から呼ぶことを想定し、異常が無ければ何も出さない。
"""

from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util

import wikilib as W

LINK_RE = re.compile(r"\[\[([^\]|#]+)")


def check(vault: str) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    oks: list[str] = []
    pages = W.load(vault)
    slugs = {p.slug for p in pages}

    # --- 索引が実体と一致しているか（生成し直して現物と比べる）---
    spec = importlib.util.spec_from_file_location(
        "wiki_index", os.path.join(os.path.dirname(os.path.abspath(__file__)), "wiki-index.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    stale = []
    built = mod.build(vault)
    for name, text in built.items():
        path = os.path.join(vault, name)
        cur = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        if mod._body(cur) != mod._body(text):
            stale.append(name)
    # 区分が消えた後に残った索引。生成されるものだけを比べると見逃す
    idx_dir = os.path.join(vault, "index")
    if os.path.isdir(idx_dir):
        stale += [f"index/{f}" for f in sorted(os.listdir(idx_dir))
                  if f.endswith(".md") and os.path.join("index", f) not in built]
    if stale:
        here = os.path.dirname(os.path.abspath(__file__))
        issues.append(f"索引がページと食い違っている（{'・'.join(stale)}）。"
                      f"直すのは python3 {os.path.join(here, 'wiki-index.py')}")
    else:
        oks.append(f"索引: ページ {len(pages)} 件と一致")

    # --- frontmatter の必須項目 ---
    missing: list[str] = []
    for p in pages:
        lack = [k for k in ("type", "sensitivity", "summary", "updated") if not p.value(k)]
        if p.type == "entity" and not p.value("category"):
            lack.append("category")
        if lack:
            missing.append(f"{p.slug}（{'・'.join(lack)}）")
    if missing:
        issues.append(f"frontmatter の必須項目が欠けたページ {len(missing)} 件: "
                      + "・".join(missing[:5]) + (" 他" if len(missing) > 5 else ""))
    else:
        oks.append("frontmatter: 必須項目は全ページに揃っている")

    # --- entity の区分（索引に載る場所が決まらない） ---
    known = {g for g, _, _ in W.GROUPS}
    unknown = sorted({g for p in pages if p.type == "entity" for g in p.groups
                      if g not in known})
    if unknown:
        # 区分の正本は vault の index/groups.json。wikilib.py の既定値は groups.json が
        # 無いときの代わりで、ここへ足すと公開テンプレートに個人の区分が入る。
        issues.append(f"区分の一覧に無い区分 {len(unknown)} 件（{'・'.join(unknown)}）。"
                      f"索引に「未分類」の節ができる。既存の区分へ寄せるか、"
                      f"vault の index/groups.json に足す")
    unfiled = [p.slug for p in pages if p.type == "entity" and not p.groups]
    if unfiled:
        issues.append(f"区分（tags の grp/…）が無い entity {len(unfiled)} 件: "
                      + "・".join(unfiled[:5]) + (" 他" if len(unfiled) > 5 else "")
                      + "。索引の「未分類」に落ちる")
    else:
        oks.append("entity の区分: 全件に grp/… がある")
    # 区分は category ごとに索引の置き場を決める。人物が grp/tool に入るとツールの索引に
    # 載り、人物を探しても見つからない（2026-09-25 に9件あった）。
    gcat = {g: c for g, _, c in W.GROUPS}
    mism = [f"{p.slug}（{p.value('category')} に grp/{g}）" for p in pages
            if p.type == "entity" for g in p.groups
            if g in gcat and gcat[g] and gcat[g] != p.value("category")]
    if mism:
        issues.append(f"category と区分が食い違う entity {len(mism)} 件: "
                      + "・".join(mism[:5]) + (" 他" if len(mism) > 5 else "")
                      + "。groups.json で category が合う区分に差し替える")
    else:
        oks.append("entity の区分: category と一致")

    # --- 1回の Read に収まらないページ ---
    big = [(p.chars, p.slug) for p in pages if p.chars > W.READ_CAP_CHARS]
    for name in ("index.md",):
        path = os.path.join(vault, name)
        if os.path.exists(path):
            n = len(open(path, encoding="utf-8").read())
            if n > W.READ_CAP_CHARS:
                big.append((n, name))
    d = os.path.join(vault, "index")
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.endswith(".md"):
                n = len(open(os.path.join(d, f), encoding="utf-8").read())
                if n > W.READ_CAP_CHARS:
                    big.append((n, f"index/{f}"))
    if big:
        big.sort(reverse=True)
        issues.append(
            f"1回の Read に全文が入らないページ {len(big)} 件（{W.READ_CAP_CHARS:,} 文字超）: "
            + "・".join(f"{s}({n:,}字)" for n, s in big[:3])
            + "。読んだつもりで後半が届かない。分割するか要約へ落とす")
    else:
        oks.append(f"ページの大きさ: 全件 {W.READ_CAP_CHARS:,} 文字以内")

    # --- リンク切れ ---
    # Obsidian は aliases でも解決するので、別名も到達先として数える。コードブロック・
    # インラインコードの中の [[...]] は書式の例示なので対象外（`[[0-9]]` のような
    # 正規表現や、雛形の `[[ページ名]]` を切れたリンクとして数えない）。
    targets = slugs | {"index", "local-notes"}
    log_dir = os.path.join(vault, "log")
    if os.path.isdir(log_dir):
        targets |= {os.path.splitext(f)[0] for f in os.listdir(log_dir) if f.endswith(".md")}
    for p in pages:
        targets |= {a for a in p.listvalue("aliases") if a}
    d = os.path.join(vault, "index")
    if os.path.isdir(d):
        targets |= {os.path.splitext(f)[0] for f in os.listdir(d) if f.endswith(".md")}
    # sources/ の md（外部資料へのポインタ等）も Obsidian はファイル名で解決する。
    # 数えないと、原資料への正しいリンクを未作成ページとして報せ続ける。
    src = os.path.join(vault, "sources")
    for root, _, fs in os.walk(src):
        targets |= {os.path.splitext(f)[0] for f in fs if f.endswith(".md")}
    dead: list[str] = []
    for p in pages:
        body = re.sub(r"```.*?```", "", p.body, flags=re.S)
        body = re.sub(r"`[^`\n]*`", "", body)
        for m in LINK_RE.finditer(body):
            t = m.group(1).strip()
            if t and t not in targets and not t.startswith(("http", "~", "/")):
                dead.append(f"{p.slug} → [[{t}]]")
    if dead:
        # 多くは「まだ作っていない人物・案件へのリンク」で、誤りではなく作成候補。
        # 誤りとして鳴らし続けると点検全体が読まれなくなるので、そう書く。
        uniq = sorted({d.split(" → ")[1] for d in dead})
        issues.append(f"未作成ページへのリンク {len(uniq)} 件（のべ {len(dead)} 回。"
                      f"作成候補。プロジェクト名など wiki のページでないものは誤記）: "
                      + "・".join(uniq[:5]) + (" 他" if len(uniq) > 5 else ""))
    else:
        oks.append("ページ間リンク: 切れなし")

    # --- 同名ページ・置き場所 ---
    seen: dict[str, str] = {}
    dup: list[str] = []
    stray: list[str] = []
    for p in pages:
        if p.folder not in W.FOLDER_TYPE:
            stray.append(os.path.relpath(p.path, vault))
        if p.slug in seen:
            dup.append(f"{p.slug}（{seen[p.slug]} と {os.path.relpath(p.path, vault)}）")
        seen[p.slug] = os.path.relpath(p.path, vault)
    if dup:
        issues.append(f"同名ページ {len(dup)} 件: " + "・".join(dup)
                      + "。[[リンク]] がどちらを指すか決まらない")
    if stray:
        issues.append(f"3フォルダの外に置かれたページ {len(stray)} 件: " + "・".join(stray))
    if not dup and not stray:
        oks.append("置き場所: concepts/entities/synthesis の3フォルダに収まっている")

    # --- sources の ingest 漏れ ---
    src_dir = os.path.join(vault, "sources")
    if os.path.isdir(src_dir):
        blob = "".join(p.raw for p in pages)
        for name in ("index.md",):
            path = os.path.join(vault, name)
            if os.path.exists(path):
                blob += open(path, encoding="utf-8").read()
        un = []
        for root, _, fs in os.walk(src_dir):
            for f in fs:
                if f.startswith("."):
                    continue
                path = os.path.join(root, f)
                stem = os.path.splitext(f)[0]
                if stem in blob or f in blob:
                    continue
                # clipping は本文の URL で引かれていることがある（Web Clipper が
                # frontmatter に source: を入れる）。ファイル名だけを見ると、
                # 既に ingest 済みのものを未 ingest と報せてしまう。
                url = ""
                if f.endswith(".md"):
                    try:
                        head = open(path, encoding="utf-8", errors="replace").read(2000)
                        m = re.search(r"^source:\s*\"?(\S+?)\"?\s*$", head, re.M)
                        url = m.group(1) if m else ""
                    except OSError:
                        url = ""
                if url and url in blob:
                    continue
                un.append(os.path.relpath(path, vault))
        if un:
            issues.append(f"sources に wiki から参照されていないファイル {len(un)} 件: "
                          + "・".join(un[:3]) + (" 他" if len(un) > 3 else "")
                          + "。ingest するか、要らなければ消す")
        else:
            oks.append("sources: 全ファイルが wiki から参照されている")

    # --- 廃止した log.md ---
    # 作業ログは 2026-09-24 に廃止した（schema「変更の記録」）。vault 直下に log.md が
    # あるのは、移行前の vault か、古い指示のまま書いている端末・セッションがあるとき。
    # どちらも放置すると書き込みが続き、Query の届かない場所に知見が溜まる。
    if os.path.exists(os.path.join(vault, "log.md")):
        issues.append("log.md がある。作業ログは廃止した（schema「変更の記録」）。"
                      "書き足された内容を該当ページへ移し、log.md は log/ へ移して凍結する。"
                      "移した後に再び現れたら、古い指示のまま動いている端末かセッションがある")
    else:
        oks.append("log.md: 無い（廃止済み）")

    return issues, oks


def main() -> int:
    ap = argparse.ArgumentParser(description="llm-wiki の健全性点検")
    ap.add_argument("--vault", default=W.vault_root())
    ap.add_argument("--verbose", action="store_true", help="正常な項目も表示する")
    args = ap.parse_args()

    if not os.path.isdir(os.path.join(args.vault, "wiki")):
        return 0  # vault が無い端末では黙って終わる

    try:
        issues, oks = check(args.vault)
    except Exception as exc:  # 点検自体がセッション開始を壊さないようにする
        print(f"⚠ llm-wiki 点検が失敗: {exc}")
        return 0

    if args.verbose:
        for o in oks:
            print(f"  OK  {o}")
    for i in issues:
        print(f"⚠ llm-wiki: {i}")
    if args.verbose and not issues:
        print("  異常なし")
    return 0


if __name__ == "__main__":
    sys.exit(main())
