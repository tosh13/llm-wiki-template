#!/usr/bin/env bash
# 全プロジェクト共通：セッション開始時に llm-wiki の名前ずれを直す。
# ~/.claude/settings.json の SessionStart フックから呼ぶ（icloud-stuck-pages.md「登録」）。
#
# iCloud for Windows は、他の端末が vault のファイルを削除して作り直すと、この端末では
# 元の名前を消して `log(1).md` のような `(数字)` 付きの名前だけを残すことがある
# （2026-09-23・09-24 に Windows の端末で確認。中身はクラウドの `log.md` と同じ1本で、
# 名前だけがずれている）。放っておくと Claude は `log.md` を見つけられず、
# `log(1).md` へ書き続けるか、新しい `log.md` を作って本当の競合を生む。
#
# 直すのは「元の名前が無く、`(数字)` 付きがちょうど1つだけある」場合に限る。
# 元の名前と並んで残っている、または `(数字)` 付きが2つ以上あるときは、どれが正か
# 機械では決められないので、動かさずに Claude へ知らせるだけにする。
# llm-wiki が無い端末・ずれが無い端末では何も出さない。
set -u
V="$HOME/llm-wiki"
[ -d "$V" ] || exit 0
cd "$V" 2>/dev/null || exit 0

fixed=""
stuck=""
# `名前(数字).md` と、ずれが重なった `名前(数字)(数字).md` の両方を拾う。
# .obsidian と .trash は対象外（前者は Obsidian の設定、後者は捨てたもの）。
while IFS= read -r f; do
  dir="$(dirname "$f")"
  base="$(basename "$f")"
  orig="$(printf '%s' "$base" | sed -E 's/(\([0-9]+\))+\.md$/.md/')"
  [ "$orig" = "$base" ] && continue
  stem="${orig%.md}"
  # 同じ元の名前へ戻る候補を数える
  n=$(find "$dir" -maxdepth 1 -type f -name "${stem}(*).md" | wc -l)
  if [ -e "$dir/$orig" ] || [ "$n" -ne 1 ]; then
    stuck="${stuck}  ${f#./}\n"
    continue
  fi
  if mv -n "$f" "$dir/$orig" 2>/dev/null && [ -e "$dir/$orig" ]; then
    to="$dir/$orig"
    fixed="${fixed}  ${f#./} -> ${to#./}\n"
  else
    stuck="${stuck}  ${f#./}\n"
  fi
done < <(find . \( -name .obsidian -o -name .trash \) -prune -o -type f -name '*([0-9]*).md' -print)

if [ -n "$fixed" ]; then
  printf 'llm-wiki: iCloud がずらした名前を元に戻しました。\n'
  printf '%b' "$fixed"
fi
if [ -n "$stuck" ]; then
  printf 'llm-wiki: (数字) 付きの名前が残っていますが、元の名前と並んでいるか候補が複数あるため動かしていません。\n'
  printf '%b' "$stuck"
  printf 'この名前のファイルへは書き込まず、中身を突き合わせてから1本にまとめてください。\n'
fi
exit 0
