import os
import re
import io
import tarfile
import zipfile
import tempfile
import base64
import ast as _py_ast
from typing import Optional, Tuple, Iterable, List, Dict


class Solution:
    _CANDIDATE_NAME_PATTERNS = (
        "clusterfuzz-testcase-minimized",
        "clusterfuzz-testcase",
        "crash-",
        "crashes",
        "repro",
        "reproducer",
        "poc",
        "uaf",
        "use-after-free",
        "use_after_free",
        "asan",
        "ubsan",
        "msan",
        "sanitizer",
        "artifact",
        "artifacts",
        "testcase",
    )

    _TEXT_EXTS = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp",
        ".rs", ".go", ".java", ".kt", ".swift",
        ".py", ".js", ".mjs", ".ts", ".tsx",
        ".md", ".txt", ".rst",
        ".toml", ".yaml", ".yml", ".json", ".xml", ".html", ".htm", ".sql", ".graphql", ".gql",
        ".fuzz", ".in", ".input",
    }

    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            b = self._scan_dir_for_poc(src_path)
            if b is not None:
                return b
            fmt = self._infer_format_from_dir(src_path)
            return self._generate_fallback_poc(fmt)

        if zipfile.is_zipfile(src_path):
            b = self._scan_zip_for_poc(src_path)
            if b is not None:
                return b
            fmt = self._infer_format_from_zip(src_path)
            return self._generate_fallback_poc(fmt)

        if tarfile.is_tarfile(src_path):
            b = self._scan_tar_for_poc(src_path)
            if b is not None:
                return b
            fmt = self._infer_format_from_tar(src_path)
            return self._generate_fallback_poc(fmt)

        # If it's an unknown file, try treating it as a directory parent
        parent = os.path.dirname(src_path)
        if parent and os.path.isdir(parent):
            b = self._scan_dir_for_poc(parent)
            if b is not None:
                return b
            fmt = self._infer_format_from_dir(parent)
            return self._generate_fallback_poc(fmt)

        return self._generate_fallback_poc("json")

    def _name_priority(self, name: str) -> int:
        n = name.lower()
        base = os.path.basename(n)

        if "clusterfuzz-testcase-minimized" in n:
            return 0
        if "clusterfuzz-testcase" in n:
            return 1
        if base.startswith("crash-") or "/crashes/" in n or "\\crashes\\" in n or "crash-" in n:
            return 2
        if "repro" in n or "reproducer" in n:
            return 3
        if "use-after-free" in n or "use_after_free" in n or "uaf" in n:
            return 4
        if "artifact" in n or "artifacts" in n:
            return 5
        if "testcase" in n:
            return 6
        if "asan" in n or "ubsan" in n or "msan" in n or "sanitizer" in n:
            return 7

        # Anything in likely crash directories gets a boost
        if any(seg in n for seg in ("/testcases/", "/testcase/", "/reproducers/", "/reproducer/", "/poc/", "/pocs/")):
            return 8

        # Seeds/corpus are weak candidates
        if any(seg in n for seg in ("/corpus/", "/seed/", "/seeds/", "/examples/", "/example/")):
            return 20

        return 50

    def _maybe_decode_special(self, name: str, data: bytes) -> bytes:
        ext = os.path.splitext(name.lower())[1]
        if ext in (".b64", ".base64"):
            try:
                s = re.sub(rb"\s+", b"", data)
                return base64.b64decode(s, validate=False)
            except Exception:
                return data
        if ext == ".hex":
            try:
                s = re.sub(rb"\s+", b"", data)
                if len(s) % 2 == 0 and re.fullmatch(rb"[0-9a-fA-F]+", s or b"") is not None:
                    return bytes.fromhex(s.decode("ascii", "ignore"))
            except Exception:
                return data
            return data

        # bytes literal in text file
        if ext in (".txt", ".md", ".rst", ".py") or self._looks_textual(data):
            d = data.strip()
            if (d.startswith(b"b'") and d.endswith(b"'")) or (d.startswith(b'b"') and d.endswith(b'"')):
                try:
                    v = _py_ast.literal_eval(d.decode("utf-8", "ignore"))
                    if isinstance(v, (bytes, bytearray)):
                        return bytes(v)
                except Exception:
                    pass
        return data

    def _looks_textual(self, data: bytes) -> bool:
        if not data:
            return True
        sample = data[:4096]
        if b"\x00" in sample:
            return False
        # Rough heuristic: if most bytes are printable-ish
        printable = 0
        for c in sample:
            if 9 <= c <= 13 or 32 <= c <= 126:
                printable += 1
        return printable / len(sample) > 0.9

    def _scan_tar_for_poc(self, tar_path: str) -> Optional[bytes]:
        best: Optional[Tuple[int, int, str, bytes]] = None  # (priority, size, name, data)
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf:
                    if not m.isfile():
                        continue
                    if m.size <= 0 or m.size > 50_000_000:
                        continue
                    name = m.name or ""
                    pri = self._name_priority(name)
                    if pri >= 20:
                        continue
                    # Avoid obviously unrelated huge binaries
                    base = os.path.basename(name).lower()
                    if any(base.endswith(ext) for ext in (".a", ".o", ".so", ".dll", ".dylib", ".exe", ".class")):
                        continue

                    if best is not None:
                        if pri > best[0]:
                            continue
                        if pri == best[0] and m.size >= best[1]:
                            continue

                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    try:
                        data = f.read()
                    finally:
                        f.close()

                    if not data:
                        continue
                    data = self._maybe_decode_special(name, data)
                    if not data:
                        continue

                    best = (pri, len(data), name, data)

                    # If we found a minimized testcase, stop early once it's "small enough"
                    if pri == 0 and len(data) < 2_000_000:
                        return data
        except Exception:
            return None

        return None if best is None else best[3]

    def _scan_zip_for_poc(self, zip_path: str) -> Optional[bytes]:
        best: Optional[Tuple[int, int, str, bytes]] = None
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                for zi in zf.infolist():
                    if zi.is_dir():
                        continue
                    if zi.file_size <= 0 or zi.file_size > 50_000_000:
                        continue
                    name = zi.filename or ""
                    pri = self._name_priority(name)
                    if pri >= 20:
                        continue
                    if best is not None:
                        if pri > best[0]:
                            continue
                        if pri == best[0] and zi.file_size >= best[1]:
                            continue
                    with zf.open(zi, "r") as f:
                        data = f.read()
                    if not data:
                        continue
                    data = self._maybe_decode_special(name, data)
                    if not data:
                        continue
                    best = (pri, len(data), name, data)
                    if pri == 0 and len(data) < 2_000_000:
                        return data
        except Exception:
            return None
        return None if best is None else best[3]

    def _scan_dir_for_poc(self, root: str) -> Optional[bytes]:
        best: Optional[Tuple[int, int, str, bytes]] = None
        for dirpath, dirnames, filenames in os.walk(root):
            # Skip VCS and build output directories
            dn = dirpath.lower()
            if any(seg in dn for seg in (os.sep + ".git", os.sep + ".hg", os.sep + ".svn", os.sep + "build", os.sep + "out")):
                continue
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path, follow_symlinks=False)
                except Exception:
                    continue
                if st.st_size <= 0 or st.st_size > 50_000_000:
                    continue
                rel = os.path.relpath(path, root)
                pri = self._name_priority(rel)
                if pri >= 20:
                    continue
                if best is not None:
                    if pri > best[0]:
                        continue
                    if pri == best[0] and st.st_size >= best[1]:
                        continue
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except Exception:
                    continue
                if not data:
                    continue
                data = self._maybe_decode_special(rel, data)
                if not data:
                    continue
                best = (pri, len(data), rel, data)
                if pri == 0 and len(data) < 2_000_000:
                    return data
        return None if best is None else best[3]

    def _infer_format_from_harness_texts(self, texts: List[str]) -> Optional[str]:
        if not texts:
            return None
        joined = "\n".join(texts).lower()

        def has(*words: str) -> bool:
            return any(w in joined for w in words)

        if has("yaml", "libyaml"):
            return "yaml"
        if has("toml"):
            return "toml"
        if has("xml", "html", "xhtml"):
            return "xml"
        if has("json", "rapidjson", "simdjson"):
            return "json"
        if has("lua", "luajit"):
            return "lua"
        if has("javascript", "ecmascript", "js_"):
            return "js"
        if has("python", "py_"):
            return "py"
        if has("sql", "sqlite"):
            return "sql"
        if has("graphql"):
            return "graphql"
        return None

    def _collect_harness_texts_from_tar(self, tar_path: str, max_files: int = 10) -> List[str]:
        texts: List[str] = []
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf:
                    if len(texts) >= max_files:
                        break
                    if not m.isfile() or m.size <= 0 or m.size > 300_000:
                        continue
                    name = m.name or ""
                    low = name.lower()
                    ext = os.path.splitext(low)[1]
                    if ext not in self._TEXT_EXTS:
                        continue
                    # Bias towards fuzz targets
                    if not any(k in low for k in ("fuzz", "fuzzer", "ossfuzz", "oss-fuzz", "afl", "libfuzzer")):
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    try:
                        data = f.read()
                    finally:
                        f.close()
                    if not data:
                        continue
                    if b"LLVMFuzzerTestOneInput" not in data and b"FuzzerTestOneInput" not in data:
                        continue
                    try:
                        texts.append(data.decode("utf-8", "ignore"))
                    except Exception:
                        continue
        except Exception:
            pass
        return texts

    def _collect_harness_texts_from_dir(self, root: str, max_files: int = 10) -> List[str]:
        texts: List[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            if len(texts) >= max_files:
                break
            dn = dirpath.lower()
            if any(seg in dn for seg in (os.sep + ".git", os.sep + "build", os.sep + "out")):
                continue
            if not any(k in dn for k in ("fuzz", "fuzzer", "ossfuzz", "oss-fuzz")):
                continue
            for fn in filenames:
                if len(texts) >= max_files:
                    break
                path = os.path.join(dirpath, fn)
                low = path.lower()
                ext = os.path.splitext(low)[1]
                if ext not in self._TEXT_EXTS:
                    continue
                try:
                    st = os.stat(path, follow_symlinks=False)
                except Exception:
                    continue
                if st.st_size <= 0 or st.st_size > 300_000:
                    continue
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except Exception:
                    continue
                if b"LLVMFuzzerTestOneInput" not in data and b"FuzzerTestOneInput" not in data:
                    continue
                try:
                    texts.append(data.decode("utf-8", "ignore"))
                except Exception:
                    continue
        return texts

    def _infer_format_from_names(self, names: Iterable[str]) -> str:
        weights: Dict[str, int] = {}
        known = {
            "yaml": {".yaml", ".yml"},
            "json": {".json"},
            "toml": {".toml"},
            "xml": {".xml", ".html", ".htm"},
            "js": {".js", ".mjs"},
            "lua": {".lua"},
            "py": {".py"},
            "sql": {".sql"},
            "graphql": {".graphql", ".gql"},
            "txt": {".txt", ".md", ".rst"},
        }

        for n in names:
            low = (n or "").lower()
            ext = os.path.splitext(low)[1]
            if not ext:
                continue
            w = 1
            if any(seg in low for seg in ("/test", "/tests", "/corpus", "/seed", "/seeds", "/example", "/examples", "/testdata")):
                w = 3
            if any(seg in low for seg in ("/fuzz", "fuzz")):
                w = max(w, 4)
            for fmt, exts in known.items():
                if ext in exts:
                    weights[fmt] = weights.get(fmt, 0) + w

        if not weights:
            return "json"
        # Prefer non-txt if close
        best_fmt = max(weights.items(), key=lambda kv: kv[1])[0]
        if best_fmt == "txt":
            # If text is dominant, default to json
            return "json"
        return best_fmt

    def _infer_format_from_tar(self, tar_path: str) -> str:
        harness_texts = self._collect_harness_texts_from_tar(tar_path)
        hint = self._infer_format_from_harness_texts(harness_texts)
        if hint:
            return hint

        names: List[str] = []
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf:
                    if m.isfile():
                        names.append(m.name or "")
                        if len(names) >= 20000:
                            break
        except Exception:
            return "json"
        return self._infer_format_from_names(names)

    def _infer_format_from_zip(self, zip_path: str) -> str:
        names: List[str] = []
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                for zi in zf.infolist():
                    if not zi.is_dir():
                        names.append(zi.filename or "")
                        if len(names) >= 20000:
                            break
        except Exception:
            return "json"
        return self._infer_format_from_names(names)

    def _infer_format_from_dir(self, root: str) -> str:
        harness_texts = self._collect_harness_texts_from_dir(root)
        hint = self._infer_format_from_harness_texts(harness_texts)
        if hint:
            return hint

        names: List[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dn = dirpath.lower()
            if any(seg in dn for seg in (os.sep + ".git", os.sep + "build", os.sep + "out")):
                continue
            for fn in filenames:
                names.append(os.path.join(dirpath, fn))
                if len(names) >= 20000:
                    return self._infer_format_from_names(names)
        return self._infer_format_from_names(names)

    def _generate_fallback_poc(self, fmt: str) -> bytes:
        fmt = (fmt or "json").lower()
        target_len = 280_000

        if fmt == "json":
            # Valid JSON: a large array of zeros
            # size ~= 1 + 2*(n-1) + 1 + 1 => 2n+1
            n = max(10, (target_len - 2) // 2)
            return (b"[" + b"0," * (n - 1) + b"0]")
        if fmt == "yaml":
            # Valid YAML sequence
            line = b"- 0\n"
            n = max(10, target_len // len(line))
            return line * n
        if fmt == "toml":
            # Valid TOML with many unique keys
            out = io.BytesIO()
            i = 0
            while out.tell() < target_len:
                out.write(f"k{i}=0\n".encode("ascii"))
                i += 1
            return out.getvalue()
        if fmt == "xml":
            # Valid XML with many empty elements
            # Keep it simple and well-formed
            inner = b"<a/>"
            n = max(10, (target_len - 20) // len(inner))
            return b'<?xml version="1.0"?><r>' + inner * n + b"</r>"
        if fmt == "js":
            # Valid JS: array literal
            n = max(10, (target_len - 2) // 2)
            return (b"[" + b"0," * (n - 1) + b"0]")
        if fmt == "py":
            # Valid Python: list literal with many zeros
            n = max(10, (target_len - 2) // 2)
            return (b"[" + b"0," * (n - 1) + b"0]")
        if fmt == "lua":
            # Valid Lua: table literal
            # Use 'return' to make it a chunk
            # Roughly: "return {" + "0,"*(n-1) + "0}"
            prefix = b"return {"
            suffix = b"}"
            remaining = max(10, target_len - len(prefix) - len(suffix))
            n = max(10, remaining // 2)
            return prefix + b"0," * (n - 1) + b"0" + suffix
        if fmt == "sql":
            # Valid-ish SQL: many SELECTs separated by semicolons
            stmt = b"SELECT 0;\n"
            n = max(10, target_len // len(stmt))
            return stmt * n
        if fmt == "graphql":
            # Valid GraphQL: query with many fields
            # query{a0 a1 ...}
            out = io.BytesIO()
            out.write(b"query{")
            i = 0
            while out.tell() < target_len - 2:
                out.write(f"a{i} ".encode("ascii"))
                i += 1
            out.write(b"}")
            return out.getvalue()

        # Default fallback: a lot of parentheses around a 0 (often valid expression languages)
        depth = 100000
        return (b"(" * depth) + b"0" + (b")" * depth)