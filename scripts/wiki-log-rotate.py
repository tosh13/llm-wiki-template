#!/usr/bin/env python3
"""log.md を月ごとに退避する。

log.md は「先頭に追記」で伸び続ける。2026-09-04 実測で 375,939 文字・408 エントリ・
4か月ぶん。全文を読む使い方はしていないので遅さの原因ではないが、この大きさになると
追記のたびに全文を読み書きする経路しか使えず、1回の Read でも全体を見渡せない。

直近ぶんだけを log.md に残し、それより古いエントリを log/YYYY-MM.md へ移す。
どのエントリも消さず、順序（新しい順）も保つ。--apply を付けない限り書き換えない。
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wikilib as W

RECENT_DAYS = 30
HEAD_RE = re.compile(r"^##\s+(\d{4})-(\d{2})-(\d{2})")


def split_entries(text: str) -> tuple[str, list[tuple[str, str]]]:
    """先頭の前書きと、(YYYY-MM, エントリ本文) の並びに分ける。"""
    lines = text.split("\n")
    starts = [i for i, l in enumerate(lines) if HEAD_RE.match(l)]
    if not starts:
        return text, []
    preamble = "\n".join(lines[: starts[0]]).rstrip("\n")
    entries = []
    for n, i in enumerate(starts):
        j = starts[n + 1] if n + 1 < len(starts) else len(lines)
        m = HEAD_RE.match(lines[i])
        entries.append((f"{m.group(1)}-{m.group(2)}", "\n".join(lines[i:j]).rstrip("\n")))
    return preamble, entries


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=W.vault_root())
    ap.add_argument("--days", type=int, default=RECENT_DAYS,
                    help=f"log.md に残す日数（既定 {RECENT_DAYS}）")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    path = os.path.join(args.vault, "log.md")
    if not os.path.exists(path):
        print(f"log.md が無い: {path}", file=sys.stderr)
        return 2
    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    preamble, entries = split_entries(text)
    if not entries:
        print("日付見出し（## YYYY-MM-DD）が見つからない。何もしない")
        return 1

    cutoff = datetime.date.today() - datetime.timedelta(days=args.days)
    keep: list[tuple[str, str]] = []
    move: dict[str, list[str]] = {}
    for month, body in entries:
        m = HEAD_RE.match(body)
        d = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d >= cutoff:
            keep.append((month, body))
        else:
            move.setdefault(month, []).append(body)

    if not move:
        print(f"退避するエントリなし（直近 {args.days} 日で {len(keep)} 件）")
        return 0

    log_dir = os.path.join(args.vault, "log")
    new_log = [preamble] if preamble else ["# 作業ログ", ""]
    if move:
        months = sorted(move, reverse=True)
        new_log.append("")
        new_log.append(f"> 直近 {args.days} 日ぶん。それ以前は "
                       + "・".join(f"[[{m}]]" for m in months) + "（log/ 配下）")
        new_log.append("")
    new_log += [b for _, b in keep]
    new_text = "\n".join(new_log).rstrip("\n") + "\n"

    print(f"log.md: {len(text):,} 文字 {len(entries)} 件"
          f" → {len(new_text):,} 文字 {len(keep)} 件")
    for month in sorted(move, reverse=True):
        bodies = move[month]
        dest = os.path.join(log_dir, f"{month}.md")
        prev = ""
        if os.path.exists(dest):
            with open(dest, encoding="utf-8") as fh:
                prev = fh.read()
        chunk = "\n\n".join(bodies)
        out = (f"# 作業ログ {month}\n\n> log.md から退避したもの（新しい順）。"
               f"直近ぶんは [[log]]。\n\n{chunk}\n")
        if prev:
            out = prev.rstrip("\n") + "\n\n" + chunk + "\n"
        print(f"  log/{month}.md ← {len(bodies)} 件（{len(out):,} 文字）")
        if args.apply:
            os.makedirs(log_dir, exist_ok=True)
            with open(dest, "w", encoding="utf-8") as fh:
                fh.write(out)

    if args.apply:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        print("適用した")
    else:
        print("（--apply で適用）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
