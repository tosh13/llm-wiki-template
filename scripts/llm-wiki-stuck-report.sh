#!/usr/bin/env bash
# 受信側の端末用：セッション開始時に、llm-wiki の殻のまま読めないページを発信側へ依頼する。
# ~/.claude/settings.json の SessionStart フックから呼ぶ。登録するのは受信側（iCloud の実体が
# 落ちてこない端末）だけで、発信側には登録しない（icloud-stuck-pages.md「登録」）。
#
# 本体は同じ場所の llm-wiki-rehydrate.py report。殻の読み出しは1件に数十秒かかり、
# 詰まったものは待っても返らないので、セッションの開始を待たせないよう裏へ回して
# すぐ戻る。報告は3時間に1回まで。結果は ~/.claude/state/llm-wiki-rehydrate/report.log。
set -u
[ -d "$HOME/llm-wiki" ] || exit 0
script="$(cd "$(dirname "$0")" && pwd)/llm-wiki-rehydrate.py"
[ -f "$script" ] || exit 0
py=""
# Windows の python3 は Microsoft Store への案内だけを出す偽物のことがあるので、動くかまで見る
for c in python3 python py; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 8))' >/dev/null 2>&1; then
    py="$c"; break
  fi
done
[ -n "$py" ] || exit 0
nohup "$py" "$script" report >/dev/null 2>&1 </dev/null &
exit 0
