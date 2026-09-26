#!/usr/bin/env python3
"""vault を現行の schema に合わせる。何度実行しても同じ結果になる。

claude-toolkit の install.py が、テンプレートを pull した直後に毎回呼ぶ。端末ごとの
手作業に頼ると、pull し忘れた端末・移行し忘れた vault が古い運用のまま残り続ける
（2026-09-26、log.md の廃止が明子さんの端末に1台も届いていなかった）。

現在の移行は1つ。作業ログの凍結（schema「変更の記録」）。vault 直下にある次のものを
`log/` へ移す。消さない。

- log.md、log-pending.md（2026-09-24 に廃止した作業ログと、その退避先）
- log(1).md・log 2.md のような名前違い（iCloud for Windows の名前ずれ・Mac の競合形）
- CLAUDE.md（vault に置いていた schema の古い写し。正本はテンプレートの schema/CLAUDE.md。
  写しが残っていると、廃止した運用を指示し続ける）

移し先に同名があれば、名前に時刻を付けて並べる。上書きしない。vault が無い端末、
移すものが無い vault では何も出さない。
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wikilib as W

FROZEN_DIR = "log"
TARGET_RE = re.compile(r"^(log|log-pending)((\(\d+\))+| \d+)?\.md$|^CLAUDE\.md$")


def free_name(dest_dir: str, name: str) -> str:
    if not os.path.lexists(os.path.join(dest_dir, name)):
        return name
    stem, ext = os.path.splitext(name)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    n = 0
    while True:
        cand = f"{stem}-{stamp}{'-' + str(n) if n else ''}{ext}"
        if not os.path.lexists(os.path.join(dest_dir, cand)):
            return cand
        n += 1


def main() -> int:
    vault = W.vault_root()
    if not os.path.isdir(vault):
        return 0
    targets = sorted(e for e in os.listdir(vault)
                     if TARGET_RE.match(e) and os.path.isfile(os.path.join(vault, e)))
    if not targets:
        return 0
    dest_dir = os.path.join(vault, FROZEN_DIR)
    os.makedirs(dest_dir, exist_ok=True)
    for name in targets:
        to = free_name(dest_dir, name)
        # 同じボリューム内の改名なので、iCloud の未ダウンロード（dataless）でも実体を取りに行かない
        shutil.move(os.path.join(vault, name), os.path.join(dest_dir, to))
        print(f"llm-wiki: {name} を {FROZEN_DIR}/{to} へ移して凍結しました（schema「変更の記録」）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
