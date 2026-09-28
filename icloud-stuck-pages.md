# iCloud の詰まりの回復

作成日：2026-09-28
改訂日：2026-09-28

vault を iCloud Drive で同期していると、端末によってはページの実体が落ちてこない、名前がずれる、という2つの症状が出る。どちらも自力では直らないので、`scripts/` の3本で機械的に直す。

## 症状

### 殻のまま読めないページ

TLS を傍受する網（企業・病院のプロキシ等）につながった端末では、iCloud の本体の転送が確率的に失敗する。失敗したページは中身の無い殻（Mac は `SF_DATALESS`、Windows は属性 `0x400000` など）のまま残り、読みにいくと数十秒から無期限に固まる。再取得の操作を何度しても直らない。

同じ端末でも大半のページは届くので、一部だけが読めないという一見矛盾した状態になる。

### 名前のずれ

iCloud for Windows は、他の端末が vault のファイルを削除して作り直すと、その端末では元の名前を消し、`log(1).md` のような `(数字)` 付きの名前だけを残すことがある。中身はクラウドの1本と同じで、名前だけがずれている。放っておくと Claude は元の名前のページを見つけられず、`(数字)` 付きへ書き続けるか、元の名前で新しく作って本当の競合を生む。

## 機序

殻が直らない理由は3段階ある。

1. 本体の転送がネットワークエラーで失敗する
2. 失敗は一律ではなく確率的に起きる（実測では87%が成功し13%が失敗した）
3. 失敗した項目は転送が抑制され（`item_throttled`）、自力で復帰しない。再取得を要求しても、抑制された項目は転送されない

抑制は項目に紐づくので、別の端末でページを削除して作り直すと新しい項目になり、抑制が外れる。ただし同じ内容で作り直すと同一の実体として扱われ、抑制も引き継がれる。1バイトでも内容を変えれば別の実体になる。依頼方式はこの2点に沿って作ってある。

傍受している網の管理者に iCloud の除外を頼めば根本から直るが、組織が iCloud の業務利用を認めていない場合は頼めない。その場合は、この失敗を直せない制約として扱う。

## 仕組み

### 依頼方式

受信側（殻が残る端末）が詰まりを見つけて依頼し、発信側（常時稼働で、vault の実体を読める端末）がそれに応じて作り直す。発信側からは受信側で何が詰まっているか見えないので、読めているページまで作り直さないよう、依頼を起点にしている。本体は `scripts/llm-wiki-rehydrate.py`。

- 受信側：セッション開始のフック `llm-wiki-stuck-report.sh` が `llm-wiki-rehydrate.py report` を裏で起動する。vault の `.md` のうち殻を1件ずつ読みにいき、90 秒で読めないものを vault の `.rehydrate/requests/<端末名>-<時刻>.txt` に書く。報告は3時間に1回までで、自分の依頼が未処理のまま残っていれば出し直さない（24時間で失効）
- 発信側：`llm-wiki-rehydrate.py serve` を30分ごとに呼ぶ。依頼に載ったページを読み、バックアップを取り、まとめて削除して2分空け、内容を変えて1回だけ書き戻す。片付いた依頼は消す
- 内容の変え方：索引（`> 生成 ` の行を持つもの）はその行の末尾に `<!-- rehydrate <時刻> -->` を付ける。`wiki-index.py --check` と `wiki-health.py` はこの行を比較から外しているので、索引の食い違いにならない。それ以外のページは末尾に同じ目印の行を置き、前回の目印は置き換える。どちらも Obsidian では見えない
- 見送るもの：作り直してから30分以内の依頼（まだ配信の途中とみなす）、読んだあとに他の端末が更新したページ、発信側でも読めないページ（次回に回す。7日で依頼ごと捨てる）、`.md` 以外、vault の外を指すパス
- 端末の状態：`~/.claude/state/llm-wiki-rehydrate/` に `report.log`・`serve.log`・作り直しの記録 `recreated.json`・作り直す前の版 `backup/<時刻>/`（30日で消す）を置く。vault には書かない

作り直しは削除を伴い、削除は全端末へ伝わる。削除から書き戻しまでの2分間は、他の端末からそのページが見えない。

### 名前ずれの修復

`llm-wiki-name-check.sh` はセッション開始時に `~/llm-wiki` を走査し、元の名前が無く `(数字)` 付きが1つだけあるときに元の名前へ戻す。元の名前と並んで残っているときや候補が2つ以上あるときは、どれが正か機械では決められないので動かさず、その一覧を Claude に知らせる。vault が無い端末やずれが無い端末では何も出さない。

改名はその端末での名前を直すだけで、中身は変えない。手で同じ改名をしたときは、差し戻しもゴミ箱への退避も起きなかった。

作り直しでページが `名前(1).md` へずれると wiki のリンクが切れるので、Windows の受信側では依頼方式より先にこちらを登録する。

## 登録

### 前提

以下のコマンドは、このリポジトリの clone を `~/.claude/llm-wiki-template` で指せることを前提にしている。claude-toolkit の `install.py` を使う端末では、`install.py` がこの別名を張る（Windows はジャンクション）。使わない端末では、パスを clone の場所に読み替える。

### 受信側

`~/.claude/settings.json` の `SessionStart` のフック列に次を足す。Windows の受信側は名前ずれの修復も足す。

```json
{
  "type": "command",
  "command": "bash -lc '\"$HOME/.claude/llm-wiki-template/scripts/llm-wiki-name-check.sh\"'",
  "timeout": 30
},
{
  "type": "command",
  "command": "bash -lc '\"$HOME/.claude/llm-wiki-template/scripts/llm-wiki-stuck-report.sh\"'",
  "timeout": 15
}
```

確かめるときは `python3 ~/.claude/llm-wiki-template/scripts/llm-wiki-rehydrate.py report --force --dry-run` を打ち、`~/.claude/state/llm-wiki-rehydrate/report.log` の最後の行（殻・読みにいった・読めないの件数）を見る。`--dry-run` を外すと依頼を書く。

### 発信側

常時稼働で、vault の全ページを読める端末を1台選ぶ。受信側と同じ網の端末は選ばない。Windows では PowerShell で次を実行する。iCloud for Windows はサインインしている間しか同期しないので、ログオン中だけ動く設定にしている。

```powershell
$exe = (& py -c "import sys; print(sys.executable)").Trim()
$w = Join-Path (Split-Path $exe) "pythonw.exe"
$script = "$env:USERPROFILE\.claude\llm-wiki-template\scripts\llm-wiki-rehydrate.py"
$action = New-ScheduledTaskAction -Execute $w -Argument "`"$script`" serve"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes 30)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 1) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName "llm-wiki-rehydrate-serve" -Action $action -Trigger $trigger -Settings $settings -Principal $principal
```

`Get-ScheduledTaskInfo -TaskName llm-wiki-rehydrate-serve` の `LastTaskResult` が `0` なら動いている。やめるときは `Unregister-ScheduledTask -TaskName llm-wiki-rehydrate-serve`。

Mac を発信側にする手順（launchd）はまだ書いていない。
