"""llm-wiki の vault を読むための共通ライブラリ。

frontmatter は YAML として妥当でない書き方が混ざっている（`related_entities: [[a]], [[b]]`
のような Obsidian のリンク列など）ため、PyYAML は使わず行ベースで読む。値は生の文字列
として保持し、解釈は呼び出し側に任せる。壊れた値を勝手に正規化すると、正本である
ページ側の記述が黙って書き換わる。
"""

from __future__ import annotations

import os
import re
import unicodedata

# 1回の Read で全文が返らなくなる境界。index.md（450行・70,235文字）を offset/limit
# 無しで読んだとき、実測で 26,676 文字・80行で打ち切られ、打ち切りの告知は無かった
# （2026-09-04 実測）。余裕を見て 24,000 文字を上限として扱う。
READ_CAP_CHARS = 24000

FOLDER_TYPE = {"concepts": "concept", "entities": "entity", "synthesis": "synthesis"}

KEY_ORDER = [
    "type", "category", "sensitivity", "tags", "aliases", "sources",
    "related_entities", "related_concepts", "created", "updated", "verified",
    "summary",
]

KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(.*)$")


class Page:
    def __init__(self, path: str, text: str):
        self.path = path
        self.raw = text
        self.slug = os.path.splitext(os.path.basename(path))[0]
        self.folder = os.path.basename(os.path.dirname(path))
        self.fm, self.body, self.has_fm = _split(text)

    # --- 読み出し ---

    def get(self, key: str, default: str = "") -> str:
        return self.fm.get(key, default)

    def value(self, key: str) -> str:
        """引用符・角括弧を落とした1行の値。"""
        v = self.fm.get(key, "")
        v = " ".join(x.strip() for x in v.splitlines() if x.strip())
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        return v.strip()

    def listvalue(self, key: str) -> list[str]:
        """`[a, b]` と block 形式の両方を要素の並びとして返す。"""
        v = self.fm.get(key, "")
        items: list[str] = []
        for line in v.splitlines():
            line = line.strip()
            if line.startswith("- "):
                items.append(line[2:].strip())
        if items:
            return [_unquote(x) for x in items if x]
        v = " ".join(v.split())
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            v = v[1:-1]
        return [_unquote(x.strip()) for x in v.split(",") if x.strip()]

    @property
    def title(self) -> str:
        """本文の H1。無ければ空。ページ自身の記述をそのまま返す（逐字コピー）。"""
        m = re.search(r"^#\s+(.+?)\s*$", self.body, re.M)
        return m.group(1).strip() if m else ""

    @property
    def type(self) -> str:
        # 正本はフォルダ（schema）。frontmatter を先に見ると、type の誤記で索引から消える
        return FOLDER_TYPE.get(self.folder) or self.value("type") or ""

    @property
    def chars(self) -> int:
        return len(self.raw)

    @property
    def groups(self) -> list[str]:
        return [t[4:] for t in self.listvalue("tags") if t.startswith("grp/")]

    # --- 書き換え ---

    def render(self, fm: dict[str, str]) -> str:
        keys = [k for k in KEY_ORDER if k in fm]
        keys += [k for k in fm if k not in keys]
        out = ["---"]
        for k in keys:
            v = fm[k]
            lines = [x for x in v.split("\n")]
            if len(lines) > 1:
                head = lines[0].strip()
                out.append(f"{k}: {head}" if head else f"{k}:")
                for line in lines[1:]:
                    if not line.strip():
                        continue
                    out.append(line if line.startswith(" ") else "  " + line)
            else:
                out.append(f"{k}: {v}")
        out.append("---")
        return "\n".join(out) + "\n" + self.body


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1]
    return s.strip()


def _split(text: str) -> tuple[dict[str, str], str, bool]:
    if not text.startswith("---"):
        return {}, text, False
    parts = text.split("\n")
    end = None
    for i, line in enumerate(parts[1:], 1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return {}, text, False
    fm: dict[str, str] = {}
    key = None
    for line in parts[1:end]:
        m = KEY_RE.match(line)
        if m and not line.startswith(" "):
            key = m.group(1)
            fm[key] = m.group(2).strip()
        elif key is not None:
            # block 形式（`sources:` の次行から `- ` が続く）は要素が1つでも
            # 行を畳んではいけない。畳むと `sources:   - URL` になって書式が壊れる。
            fm[key] = fm[key] + "\n" + line
    body = "\n".join(parts[end + 1:])
    return fm, body, True


def load(vault: str) -> list[Page]:
    """wiki/ 配下の全ページ。直下に置かれたページも拾う（schema 違反として検出したい）。"""
    pages = []
    for root, dirs, files in os.walk(os.path.join(vault, "wiki")):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in sorted(files):
            if not f.endswith(".md"):
                continue
            p = os.path.join(root, f)
            with open(p, encoding="utf-8", errors="replace") as fh:
                pages.append(Page(p, fh.read()))
    return pages


def trim(text: str, limit: int) -> str:
    """索引1行ぶんに詰める。句点・読点の手前で切り、切ったことを示す。"""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for sep in ("。", "．", "、", "／", " "):
        i = cut.rfind(sep)
        if i >= limit * 0.6:
            return cut[: i + (1 if sep in "。．" else 0)].rstrip("、／ ") + "…"
    return cut.rstrip() + "…"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"[\s。、・「」（）()【】\[\]—–:：/,.]", "", s)


def vault_root() -> str:
    return os.environ.get("LLM_WIKI_VAULT", os.path.expanduser("~/llm-wiki"))


# entity の区分。索引のどのファイルに載るかを決める。
#
# 区分の中身は環境ごとに違う（誰と何の仕事をしているか、そのもの）ので、正本は
# vault 側の `index/groups.json` に置く。テンプレートには一般的な既定だけを持たせ、
# 個人の分類をリポジトリへ持ち込まない（配布境界＝リポジトリ境界）。
DEFAULT_GROUPS = [
    ("self", "人物 — 本人", "person"),
    ("family", "人物 — 家族", "person"),
    ("colleague", "人物 — 同僚・仕事関係", "person"),
    ("external", "人物 — 外部・その他", "person"),
    ("org", "組織", "organization"),
    ("regulation", "法令・規制", "regulation"),
    ("tool", "ツール・手順", "tool"),
]


def load_groups(vault: str | None = None) -> list[tuple[str, str, str]]:
    """`<vault>/index/groups.json` があればそれを、無ければ既定を返す。

    形式は {"groups": [{"slug": ..., "label": ..., "category": ...}, ...]}。
    並び順がそのまま索引の節の順序になる。
    """
    import json
    path = os.path.join(vault or vault_root(), "index", "groups.json")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        out = [(g["slug"], g["label"], g.get("category", "person"))
               for g in data.get("groups", []) if g.get("slug") and g.get("label")]
        return out or DEFAULT_GROUPS
    except (OSError, ValueError, KeyError, TypeError):
        return DEFAULT_GROUPS


GROUPS = load_groups()
GROUP_LABEL = {g: label for g, label, _ in GROUPS}
GROUP_CATEGORY = {g: cat for g, _, cat in GROUPS}


def value_summary(page: "Page") -> str:
    """索引に出す1行。summary が無ければ H1 で代用する（生成を止めない）。"""
    return page.value("summary") or page.title
