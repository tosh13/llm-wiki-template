#!/usr/bin/env python3
"""llm-wiki の詰まりを、受信側の依頼に応じて発信側で作り直す。

  report  受信側（iCloud の実体が落ちてこない端末）で使う。殻のまま読めないページを探し、
          vault の .rehydrate/requests/ へ依頼を1ファイルとして書く。
          セッション開始のフック llm-wiki-stuck-report.sh から裏で呼ばれる。
  serve   発信側（常時稼働で、vault の実体を読める端末）で使う。依頼を読み、該当ページを
          内容を変えて作り直してから依頼を消す。タスクスケジューラから定期的に呼ぶ。

作り直しが効く理由と、内容を変える必要がある理由は
icloud-stuck-pages.md「機序」。抑制（item_throttled）は
項目に紐づくので、削除して別の内容で作り直すと新しい項目になって外れる。
同じ内容だと同一の実体として扱われ、抑制も引き継がれる。

作り直すのは .md だけ。内容の変え方は2通りで、どちらも読み手には見えない。
  - `> 生成 ` で始まる行がある（wiki-index.py が作る索引）→ その行の末尾に目印を付ける。
    wiki-health.py の索引の鮮度判定はこの行を比較から外しているので、食い違いにならない
  - それ以外 → 末尾に目印の行 `<!-- rehydrate YYYYMMDDTHHMMSS -->` を置く（前回の目印は置き換える）

端末の状態（最終実行時刻・作り直しの記録・バックアップ・ログ）は
~/.claude/state/llm-wiki-rehydrate/ に置き、vault（iCloud）には書かない。
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import socket
import sys
import threading
import time
from pathlib import Path

VAULT = Path.home() / "llm-wiki"
STATE = Path(os.environ.get("LLM_WIKI_REHYDRATE_STATE") or Path.home() / ".claude" / "state" / "llm-wiki-rehydrate")
REQ_SUB = Path(".rehydrate") / "requests"
SKIP_DIRS = {".rehydrate", ".obsidian", ".trash"}

# Windows: FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS / RECALL_ON_OPEN / OFFLINE
WIN_SHELL = 0x400000 | 0x40000 | 0x1000
# macOS: SF_DATALESS
MAC_DATALESS = 0x40000000

MARK = "<!-- rehydrate {} -->"
MARK_RE = re.compile(r"<!-- rehydrate \d{8}T\d{6} -->")
GEN_PREFIX = "> 生成 "

REPORT_INTERVAL = 3 * 3600      # 受信側が報告する最短間隔
PENDING_TTL = 24 * 3600         # 自分の依頼が未処理のまま残っていても、これを過ぎたら出し直す
GRACE = 30 * 60                 # 作り直してからこの時間内の依頼は、配信待ちとみなして捨てる
REQUEST_TTL = 7 * 86400         # 処理できないまま残った依頼の寿命
BACKUP_TTL = 30 * 86400


def now() -> dt.datetime:
    return dt.datetime.now().astimezone()


def stamp(t: dt.datetime) -> str:
    return t.strftime("%Y%m%dT%H%M%S")


def host() -> str:
    h = os.environ.get("COMPUTERNAME") or socket.gethostname().split(".")[0]
    return re.sub(r"[^A-Za-z0-9_-]", "", h) or "unknown"


def log(name: str, msg: str) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    line = f"{now().isoformat(timespec='seconds')} {msg}"
    with open(STATE / f"{name}.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")
    if sys.stdout and sys.stdout.isatty():
        print(line)


def is_shell(p: Path) -> bool:
    """実体を持たない（読むとダウンロードが走る）かを、中身に触れずに判定する。"""
    st = os.stat(p)
    return bool(getattr(st, "st_file_attributes", 0) & WIN_SHELL
                or getattr(st, "st_flags", 0) & MAC_DATALESS)


def read_with_timeout(p: Path, timeout: float) -> tuple[bytes | None, str]:
    """読めなければ (None, エラー文)。殻の読み出しは無期限に待つことがあるので別スレッドで読む。"""
    box: dict = {}

    def run() -> None:
        try:
            box["data"] = p.read_bytes()
        except OSError as e:
            box["err"] = f"{type(e).__name__}: {e}"

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return None, f"{timeout:.0f} 秒で読み終わらない"
    if "err" in box:
        return None, box["err"]
    return box["data"], ""


def iter_pages(vault: Path):
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".md"):
                yield Path(root) / f


def valid_rel(vault: Path, rel: str) -> Path | None:
    rel = rel.strip().replace("\\", "/")
    if not rel or rel.startswith("#") or rel.startswith("/") or ":" in rel:
        return None
    parts = rel.split("/")
    if ".." in parts or parts[0] in SKIP_DIRS or not rel.endswith(".md"):
        return None
    p = vault.joinpath(*parts)
    return p if p.is_file() else None


def add_marker(data: bytes, ts: str) -> bytes:
    text = data.decode("utf-8")
    nl = "\r\n" if "\r\n" in text else "\n"
    mark = MARK.format(ts)
    lines = text.split(nl)
    for i, line in enumerate(lines):
        if line.startswith(GEN_PREFIX):
            base = MARK_RE.sub("", line).rstrip()
            lines[i] = f"{base} {mark}"
            return nl.join(lines).encode("utf-8")
    # 末尾の空行と前回の目印を外してから、目印の行を1つだけ置く
    while lines and (lines[-1].strip() == "" or MARK_RE.fullmatch(lines[-1].strip())):
        lines.pop()
    return (nl.join(lines) + nl + nl + mark + nl).encode("utf-8")


def conflicts(p: Path) -> list[str]:
    stem = p.stem
    out = []
    for q in p.parent.iterdir():
        if q == p or q.suffix != ".md":
            continue
        s = q.stem
        if re.fullmatch(re.escape(stem) + r"(\(\d+\))+", s) or re.fullmatch(re.escape(stem) + r" \d+", s):
            out.append(q.name)
    return out


# ---------------------------------------------------------------- report


def cmd_report(a: argparse.Namespace) -> int:
    vault = a.vault
    if not vault.is_dir():
        return 0
    STATE.mkdir(parents=True, exist_ok=True)
    last = STATE / "last-report"
    if not a.force and last.exists() and time.time() - last.stat().st_mtime < REPORT_INTERVAL:
        return 0
    last.touch()

    me = host()
    req_dir = vault / REQ_SUB
    if not a.force and req_dir.is_dir():
        mine = [q for q in req_dir.glob(f"{me}-*.txt")
                if time.time() - q.stat().st_mtime < PENDING_TTL]
        if mine:
            log("report", f"未処理の依頼が残っているので出さない: {mine[0].name}")
            return 0

    t0 = time.time()
    shells = [p for p in iter_pages(vault) if is_shell(p)]
    stuck: list[tuple[str, str]] = []
    tried = 0
    for p in shells[: a.max_files]:
        if time.time() - t0 > a.budget:
            break
        tried += 1
        data, err = read_with_timeout(p, a.timeout)
        if data is None:
            stuck.append((p.relative_to(vault).as_posix(), err))
    log("report", f"殻 {len(shells)} 件、読みにいった {tried} 件、読めない {len(stuck)} 件")
    for rel, err in stuck:
        log("report", f"  読めない: {rel} :: {err}")
    if not stuck:
        return 0

    t = now()
    body = [f"# host: {me}", f"# created: {t.isoformat(timespec='seconds')}"]
    body += [rel for rel, _ in stuck]
    name = f"{me}-{stamp(t)}.txt"
    if a.dry_run:
        log("report", f"（dry-run）依頼 {name} は書かない")
        return 0
    tmp = STATE / name
    tmp.write_text("\n".join(body) + "\n", encoding="utf-8")
    req_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(tmp, req_dir / name)     # vault へは1回だけ書く
    tmp.unlink()
    log("report", f"依頼を書いた: {REQ_SUB.as_posix()}/{name}")
    return 0


# ---------------------------------------------------------------- serve


def load_state() -> dict:
    try:
        return json.loads((STATE / "recreated.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(s: dict) -> None:
    (STATE / "recreated.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


def parse_request(data: bytes, fallback: float) -> tuple[float, list[str]]:
    created = fallback
    rels = []
    for line in data.decode("utf-8", "replace").splitlines():
        if line.startswith("# created:"):
            try:
                created = dt.datetime.fromisoformat(line.split(":", 1)[1].strip()).timestamp()
            except ValueError:
                pass
        elif line.strip() and not line.startswith("#"):
            rels.append(line.strip())
    return created, rels


def cmd_serve(a: argparse.Namespace) -> int:
    vault = a.vault
    req_dir = vault / REQ_SUB
    if not req_dir.is_dir():
        return 0
    STATE.mkdir(parents=True, exist_ok=True)
    lock = STATE / "serve.lock"
    try:
        if lock.exists() and time.time() - lock.stat().st_mtime > 3600:
            lock.unlink()
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    except FileExistsError:
        return 0
    try:
        return serve(a, vault, req_dir)
    finally:
        lock.unlink(missing_ok=True)


def serve(a: argparse.Namespace, vault: Path, req_dir: Path) -> int:
    reqs = sorted(req_dir.glob("*.txt"))
    if not reqs:
        return 0
    state = load_state()
    t = now()
    ts = stamp(t)

    # 依頼ごとに、そこに載ったパスと依頼の時刻を集める
    wants: dict[str, float] = {}          # rel -> いちばん新しい依頼の時刻
    req_rels: dict[Path, list[str]] = {}
    for q in reqs:
        data, err = read_with_timeout(q, a.timeout)
        if data is None:
            log("serve", f"依頼を読めない（次回に回す）: {q.name} :: {err}")
            continue
        created, rels = parse_request(data, q.stat().st_mtime)
        if time.time() - created > REQUEST_TTL:
            log("serve", f"期限切れの依頼を捨てる: {q.name}")
            if not a.dry_run:
                q.unlink(missing_ok=True)
            continue
        req_rels[q] = rels
        for rel in rels:
            wants[rel] = max(wants.get(rel, 0), created)

    done: set[str] = set()                # 片付いた（作り直した・不要・不正）パス
    prepared = []                         # (rel, path, old_bytes, new_bytes, (size, mtime_ns))
    for rel, created in sorted(wants.items()):
        p = valid_rel(vault, rel)
        if p is None or p.relative_to(vault).as_posix() != rel:
            log("serve", f"対象外のパスを捨てる: {rel}")
            done.add(rel)
            continue
        prev = state.get(rel)
        if prev and created < prev + GRACE:
            log("serve", f"作り直してから間もない依頼なので見送る: {rel}")
            done.add(rel)
            continue
        data, err = read_with_timeout(p, a.timeout)
        if data is None:
            log("serve", f"発信側でも読めない（次回に回す）: {rel} :: {err}")
            continue
        try:
            new = add_marker(data, ts)
        except UnicodeDecodeError:
            log("serve", f"UTF-8 でないので作り直さない: {rel}")
            done.add(rel)
            continue
        st = os.stat(p)
        prepared.append((rel, p, data, new, (st.st_size, st.st_mtime_ns)))

    if prepared and not a.dry_run:
        bdir = STATE / "backup" / ts
        for rel, p, old, _, _ in prepared:
            b = bdir / rel
            b.parent.mkdir(parents=True, exist_ok=True)
            b.write_bytes(old)
            if hashlib.sha256(b.read_bytes()).digest() != hashlib.sha256(old).digest():
                log("serve", f"バックアップの検証に失敗したので中止: {rel}")
                return 1
        # 削除をまとめて行い、間を空けてから作る（手順書「厳守事項」）
        removed = []
        for item in prepared:
            rel, p, _, _, sig = item
            st = os.stat(p)
            if (st.st_size, st.st_mtime_ns) != sig:
                log("serve", f"読んだあとに更新されたので今回は見送る: {rel}")
                continue
            p.unlink()
            removed.append(item)
        if removed:
            time.sleep(a.wait)
        for rel, p, _, new, _ in removed:
            tmp = STATE / "tmp.md"
            tmp.write_bytes(new)
            if p.exists():
                log("serve", f"削除のあいだに別の版が置かれたので書かない: {rel}")
                continue
            shutil.copyfile(tmp, p)       # vault へは1回だけ書く
            tmp.unlink()
            if p.read_bytes() != new:
                log("serve", f"書き戻しの検証に失敗: {rel}（バックアップ {bdir / rel}）")
                continue
            state[rel] = time.time()
            done.add(rel)
            log("serve", f"作り直した: {rel}（{len(new)} バイト）")
        save_state(state)
        time.sleep(min(a.wait, 10))
        for rel, p, _, _, _ in removed:
            c = conflicts(p)
            if c:
                log("serve", f"競合らしい名前が出ている: {rel} の隣に {'・'.join(c)}")
    elif prepared:
        for rel, *_ in prepared:
            log("serve", f"（dry-run）作り直す予定: {rel}")

    for q, rels in req_rels.items():
        left = [r for r in rels if r not in done]
        if not left and not a.dry_run:
            q.unlink(missing_ok=True)
            log("serve", f"依頼を片付けた: {q.name}")

    cut = time.time() - BACKUP_TTL
    for d in (STATE / "backup").glob("*") if (STATE / "backup").is_dir() else []:
        if d.is_dir() and d.stat().st_mtime < cut:
            shutil.rmtree(d, ignore_errors=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=["report", "serve"])
    ap.add_argument("--vault", type=Path, default=VAULT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="report: 間隔と未処理の依頼を無視する")
    ap.add_argument("--timeout", type=float, default=90,
                    help="1ファイルを読む待ち時間（秒）。普通の網でも殻の読み出しに30秒余りかかる")
    ap.add_argument("--max-files", type=int, default=80, help="report: 読みにいく殻の上限")
    ap.add_argument("--budget", type=float, default=600, help="report: 全体の持ち時間（秒）")
    ap.add_argument("--wait", type=float, default=120, help="serve: 削除から作成までの間隔（秒）")
    a = ap.parse_args()
    rc = cmd_report(a) if a.mode == "report" else cmd_serve(a)
    if sys.stdout:          # pythonw（タスクスケジューラ）では None
        sys.stdout.flush()
    os._exit(rc)        # 読み出しで止まったスレッドを待たずに終える


if __name__ == "__main__":
    main()
