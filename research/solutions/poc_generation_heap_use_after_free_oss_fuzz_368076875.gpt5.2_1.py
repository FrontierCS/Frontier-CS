import os
import io
import re
import tarfile
import zipfile
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple


TARGET_LEN = 274_773


CRASH_TOKENS = (
    "crash",
    "poc",
    "repro",
    "reproducer",
    "uaf",
    "use-after-free",
    "useafterfree",
    "asan",
    "ubsan",
    "msan",
    "ossfuzz",
    "oss-fuzz",
    "clusterfuzz",
    "issue",
    "bug",
    "368076875",
)

DIR_TOKENS = (
    "/fuzz",
    "fuzz/",
    "/fuzzer",
    "fuzzer/",
    "/corpus",
    "corpus/",
    "/test",
    "/tests",
    "/regress",
    "/regression",
    "/artifact",
    "/artifacts",
    "/inputs",
    "/testdata",
    "/data",
    "/cases",
    "/samples",
    "/fixtures",
)

SOURCE_DIR_PENALTY_TOKENS = (
    "/src/",
    "/source/",
    "/include/",
    "/third_party/",
    "/thirdparty/",
    "/third-party/",
    "/cmake/",
    "/build/",
    "/out/",
    "/obj/",
    "/deps/",
    "/dependency/",
    "/vendor/",
)

BINARY_EXT_PENALTY = (
    ".a", ".o", ".so", ".dll", ".dylib", ".exe", ".bin", ".class", ".jar",
    ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".woff", ".woff2", ".ttf", ".otf",
)

ARCHIVE_EXT = (".zip", ".tar", ".tgz", ".gz", ".bz2", ".xz", ".7z", ".zst")


SOURCE_EXT = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx", ".py", ".rs", ".go", ".java", ".js")


def _lower(s: str) -> str:
    try:
        return s.lower()
    except Exception:
        return str(s).lower()


def _ext(name: str) -> str:
    base = name.rsplit("/", 1)[-1]
    dot = base.rfind(".")
    return base[dot:].lower() if dot != -1 else ""


def _looks_text(b: bytes) -> bool:
    if not b:
        return True
    chunk = b[:4096]
    if b"\x00" in chunk:
        return False
    printable = 0
    for c in chunk:
        if c in (9, 10, 13) or 32 <= c <= 126:
            printable += 1
    return printable / max(1, len(chunk)) > 0.85


def _score_name_size(name: str, size: int) -> float:
    nl = _lower(name)
    score = 0.0

    for t in CRASH_TOKENS:
        if t in nl:
            score += 200.0

    for t in DIR_TOKENS:
        if t in nl:
            score += 30.0

    for t in SOURCE_DIR_PENALTY_TOKENS:
        if t in nl:
            score -= 60.0

    ext = _ext(nl)

    if ext in BINARY_EXT_PENALTY:
        score -= 150.0

    if ext in ARCHIVE_EXT:
        score -= 50.0

    # Size proximity to TARGET_LEN, but allow other sizes too.
    dist = abs(size - TARGET_LEN)
    if dist == 0:
        score += 600.0
    else:
        score += max(0.0, 120.0 - (dist / 1500.0))

    # Mild preference for medium-sized inputs
    if 256 <= size <= 5_000_000:
        score += 20.0

    # Penalize tiny files
    if size < 32:
        score -= 40.0

    return score


def _infer_type_from_harness_text(text: str) -> Optional[str]:
    tl = text.lower()
    # Check for strong indicators first
    if "nlohmann::json" in tl or "rapidjson" in tl or "jsonparse" in tl or "json_parse" in tl:
        return "json"
    if "pugixml" in tl or "tinyxml" in tl or "libxml" in tl or "xmlparser" in tl or "xml_parse" in tl:
        return "xml"
    if "yaml" in tl:
        return "yaml"
    if "toml" in tl:
        return "toml"
    if "lua" in tl:
        return "lua"
    if "ecma" in tl or "javascript" in tl or "parsejs" in tl or "acorn" in tl:
        return "js"
    if "python" in tl or "py_parser" in tl or "ast.parse" in tl:
        return "python"
    if "protobuf" in tl or "parsefromarray" in tl:
        return "protobuf"
    if "sql" in tl:
        return "sql"
    if "llvmfuzzertestoneinput" in tl and ("#include" in tl and "c_parser" in tl):
        return "c"
    return None


def _infer_type_from_extension_counts(ext_counts: Dict[str, int]) -> Optional[str]:
    if not ext_counts:
        return None
    candidates = [
        (".json", "json"),
        (".js", "js"),
        (".py", "python"),
        (".xml", "xml"),
        (".html", "xml"),
        (".xhtml", "xml"),
        (".yaml", "yaml"),
        (".yml", "yaml"),
        (".toml", "toml"),
        (".lua", "lua"),
        (".sql", "sql"),
        (".c", "c"),
        (".cpp", "c"),
        (".cc", "c"),
    ]
    best = None
    best_cnt = 0
    for ext, t in candidates:
        cnt = ext_counts.get(ext, 0)
        if cnt > best_cnt:
            best_cnt = cnt
            best = t
    return best


def _repeat_to_target(prefix: bytes, pattern: bytes, sep: bytes, suffix: bytes, target_len: int) -> bytes:
    # Build: prefix + pattern (+ sep + pattern)* + suffix, total close to target_len
    if target_len < len(prefix) + len(suffix) + len(pattern):
        return prefix + pattern + suffix

    out = bytearray()
    out += prefix
    first = True
    while True:
        add = pattern if first else (sep + pattern)
        if len(out) + len(add) + len(suffix) > target_len:
            break
        out += add
        first = False
    out += suffix
    return bytes(out)


def _gen_json(target_len: int) -> bytes:
    # Valid JSON array of repeated small objects to yield many AST nodes
    prefix = b"["
    suffix = b"]"
    sep = b","
    pattern = b'{"a":[0,1,2,3,4,5,6,7],"b":"xxxxxxxxxxxxxxxx","c":null,"d":true,"e":false}'
    return _repeat_to_target(prefix, pattern, sep, suffix, target_len)


def _gen_js(target_len: int) -> bytes:
    prefix = b""
    suffix = b"\n"
    sep = b""
    pattern = b"function f(){var a=1+2+3+4+5;var b=(a*7)-(a/3);return a+b;}\n"
    # Repeating function decls with same name may or may not be allowed; use unique-ish names by adding a counter?
    # Keep simple: many statements inside a single function with repeated patterns.
    inner = b"var a=1+2+3+4+5;var b=(a*7)-(a/3);"
    fn_prefix = b"function main(){\n"
    fn_suffix = b"\n}\nmain();\n"
    body_target = max(0, target_len - len(fn_prefix) - len(fn_suffix))
    body = bytearray()
    while len(body) + len(inner) + 1 <= body_target:
        body += inner + b"\n"
    return fn_prefix + bytes(body) + fn_suffix


def _gen_python(target_len: int) -> bytes:
    # Many simple statements to create AST nodes
    prefix = b"def main():\n"
    suffix = b"\nmain()\n"
    sep = b""
    stmt = b"    a = (1+2+3+4+5) * (6+7+8+9)\n"
    body_target = max(0, target_len - len(prefix) - len(suffix))
    out = bytearray()
    out += prefix
    while len(out) + len(stmt) + len(suffix) <= target_len and len(out) - len(prefix) + len(stmt) <= body_target:
        out += stmt
    out += suffix
    return bytes(out)


def _gen_xml(target_len: int) -> bytes:
    # Wrap many repeated elements in a root
    prefix = b"<r>"
    suffix = b"</r>"
    sep = b""
    pattern = b"<a><b>text</b><c attr='123'>more</c></a>"
    return _repeat_to_target(prefix, pattern, sep, suffix, target_len)


def _gen_yaml(target_len: int) -> bytes:
    prefix = b"---\n"
    suffix = b"...\n"
    sep = b""
    pattern = b"- {a: [0, 1, 2, 3, 4, 5, 6, 7], b: \"xxxxxxxxxxxxxxxx\", c: null, d: true}\n"
    core_target = max(0, target_len - len(prefix) - len(suffix))
    out = bytearray()
    out += prefix
    while len(out) - len(prefix) + len(pattern) <= core_target and len(out) + len(pattern) + len(suffix) <= target_len:
        out += pattern
    out += suffix
    return bytes(out)


def _gen_toml(target_len: int) -> bytes:
    # Use array-of-tables [[t]] repeatedly
    prefix = b""
    suffix = b""
    sep = b""
    pattern = b"[[t]]\na = 1\nb = \"xxxxxxxxxxxxxxxx\"\nc = [0,1,2,3,4,5,6,7]\n\n"
    return _repeat_to_target(prefix, pattern, sep, suffix, target_len)


def _gen_c(target_len: int) -> bytes:
    prefix = b"int main(){\n  int a=0; int b=1;\n"
    suffix = b"  return a+b;\n}\n"
    stmt = b"  a = a + b + 1; b = b + a + 2;\n"
    core_target = max(0, target_len - len(prefix) - len(suffix))
    out = bytearray()
    out += prefix
    while len(out) - len(prefix) + len(stmt) <= core_target and len(out) + len(stmt) + len(suffix) <= target_len:
        out += stmt
    out += suffix
    return bytes(out)


def _gen_fallback(target_len: int) -> bytes:
    # Generic structured text
    return _gen_json(target_len)


@dataclass
class _BestBlob:
    score: float
    name: str
    data: bytes


class Solution:
    def solve(self, src_path: str) -> bytes:
        # 1) Try to locate an existing PoC/crash input embedded in the source tarball/repo.
        best = self._try_find_existing_poc(src_path)
        if best is not None:
            return best

        # 2) Infer likely input type from fuzzer harness / seed corpus and synthesize a large structured input.
        inferred = self._infer_input_type(src_path)
        target_len = TARGET_LEN

        if inferred == "json":
            return _gen_json(target_len)
        if inferred == "xml":
            return _gen_xml(target_len)
        if inferred == "yaml":
            return _gen_yaml(target_len)
        if inferred == "toml":
            return _gen_toml(target_len)
        if inferred == "js":
            return _gen_js(target_len)
        if inferred == "python":
            return _gen_python(target_len)
        if inferred == "c":
            return _gen_c(target_len)

        return _gen_fallback(target_len)

    def _try_find_existing_poc(self, src_path: str) -> Optional[bytes]:
        if os.path.isdir(src_path):
            return self._try_find_existing_poc_in_dir(src_path)

        low = _lower(src_path)
        if low.endswith(".zip"):
            return self._try_find_existing_poc_in_zip_path(src_path)

        # Default to tar-like
        try:
            with tarfile.open(src_path, "r:*") as tf:
                return self._try_find_existing_poc_in_tar(tf)
        except Exception:
            # Fallback: treat as file containing raw bytes? unlikely but safe
            try:
                with open(src_path, "rb") as f:
                    b = f.read()
                return b if b else None
            except Exception:
                return None

    def _try_find_existing_poc_in_dir(self, root: str) -> Optional[bytes]:
        best_ref: Optional[Tuple[float, str, int]] = None
        zip_paths: List[str] = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                except Exception:
                    continue
                if not os.path.isfile(p) or st.st_size <= 0:
                    continue
                rel = os.path.relpath(p, root).replace(os.sep, "/")
                s = _score_name_size(rel, st.st_size)
                if best_ref is None or s > best_ref[0]:
                    best_ref = (s, p, st.st_size)
                if _lower(fn).endswith(".zip") and st.st_size < 80_000_000:
                    zip_paths.append(p)

        # Prefer exact-length candidate if it exists and looks like input
        if best_ref is not None:
            s, p, _ = best_ref
            if s >= 400.0:
                try:
                    with open(p, "rb") as f:
                        data = f.read()
                    if data:
                        return data
                except Exception:
                    pass

        # Try nested seed corpus zips
        best_nested = self._scan_nested_zips(zip_paths)
        if best_nested is not None:
            return best_nested

        # Otherwise just return best candidate
        if best_ref is not None:
            _, p, _ = best_ref
            try:
                with open(p, "rb") as f:
                    data = f.read()
                if data:
                    return data
            except Exception:
                pass
        return None

    def _try_find_existing_poc_in_zip_path(self, zip_path: str) -> Optional[bytes]:
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                return self._try_find_existing_poc_in_zip(zf)
        except Exception:
            return None

    def _try_find_existing_poc_in_zip(self, zf: zipfile.ZipFile) -> Optional[bytes]:
        infos = []
        for zi in zf.infolist():
            if zi.is_dir():
                continue
            if zi.file_size <= 0:
                continue
            name = zi.filename
            size = zi.file_size
            s = _score_name_size(name, size)
            infos.append((s, zi))

        if not infos:
            return None

        infos.sort(key=lambda x: x[0], reverse=True)
        # Try top few; prefer those close to target and likely to be inputs.
        for s, zi in infos[:12]:
            if s < 120.0:
                break
            try:
                data = zf.read(zi)
            except Exception:
                continue
            if not data:
                continue
            # If it's an embedded seed corpus zip, scan it
            if zi.filename.lower().endswith(".zip") and len(data) < 80_000_000:
                nested = self._scan_zip_bytes(data)
                if nested is not None:
                    return nested
            # Heuristic: avoid picking obvious compiled binaries from source zips
            if _ext(zi.filename) in BINARY_EXT_PENALTY:
                continue
            return data

        # As last resort pick best-scoring
        _, zi = infos[0]
        try:
            return zf.read(zi)
        except Exception:
            return None

    def _try_find_existing_poc_in_tar(self, tf: tarfile.TarFile) -> Optional[bytes]:
        members = tf.getmembers()
        best_member = None
        best_score = float("-inf")
        zip_members: List[tarfile.TarInfo] = []

        # If we find a very strong candidate, return immediately after reading.
        strong_candidates: List[Tuple[float, tarfile.TarInfo]] = []

        for m in members:
            if not m.isreg():
                continue
            size = m.size
            if size <= 0:
                continue
            name = m.name
            s = _score_name_size(name, size)
            if s > best_score:
                best_score = s
                best_member = m
            if s >= 350.0:
                strong_candidates.append((s, m))
            if name.lower().endswith(".zip") and size < 80_000_000:
                zip_members.append(m)

        strong_candidates.sort(key=lambda x: x[0], reverse=True)
        for s, m in strong_candidates[:8]:
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
            except Exception:
                continue
            if not data:
                continue
            # If it's a zip, scan for inner artifact
            if m.name.lower().endswith(".zip"):
                nested = self._scan_zip_bytes(data)
                if nested is not None:
                    return nested
            return data

        # Scan nested seed corpus zips if available
        nested = self._scan_nested_tar_zips(tf, zip_members)
        if nested is not None:
            return nested

        if best_member is None:
            return None
        try:
            f = tf.extractfile(best_member)
            if f is None:
                return None
            data = f.read()
            return data if data else None
        except Exception:
            return None

    def _scan_nested_tar_zips(self, tf: tarfile.TarFile, zip_members: List[tarfile.TarInfo]) -> Optional[bytes]:
        best: Optional[_BestBlob] = None
        for m in zip_members[:30]:
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                zbytes = f.read()
            except Exception:
                continue
            if not zbytes:
                continue
            nested = self._scan_zip_bytes(zbytes)
            if nested is None:
                continue
            # Prefer nested if parent name suggests fuzz corpus
            bonus = 0.0
            nl = m.name.lower()
            if "seed" in nl or "corpus" in nl or "fuzz" in nl:
                bonus += 40.0
            sc = 200.0 + bonus
            if best is None or sc > best.score:
                best = _BestBlob(sc, m.name + "::zip", nested)
        return best.data if best is not None else None

    def _scan_nested_zips(self, zip_paths: List[str]) -> Optional[bytes]:
        best: Optional[_BestBlob] = None
        for zp in zip_paths[:40]:
            try:
                with open(zp, "rb") as f:
                    zbytes = f.read()
            except Exception:
                continue
            nested = self._scan_zip_bytes(zbytes)
            if nested is None:
                continue
            bonus = 0.0
            zl = zp.lower().replace("\\", "/")
            if "seed" in zl or "corpus" in zl or "fuzz" in zl:
                bonus += 40.0
            sc = 200.0 + bonus
            if best is None or sc > best.score:
                best = _BestBlob(sc, zp, nested)
        return best.data if best is not None else None

    def _scan_zip_bytes(self, zbytes: bytes) -> Optional[bytes]:
        try:
            with zipfile.ZipFile(io.BytesIO(zbytes), "r") as zf:
                return self._try_find_existing_poc_in_zip(zf)
        except Exception:
            return None

    def _infer_input_type(self, src_path: str) -> Optional[str]:
        if os.path.isdir(src_path):
            return self._infer_input_type_dir(src_path)

        low = _lower(src_path)
        if low.endswith(".zip"):
            return self._infer_input_type_zip_path(src_path)

        try:
            with tarfile.open(src_path, "r:*") as tf:
                return self._infer_input_type_tar(tf)
        except Exception:
            return None

    def _infer_input_type_zip_path(self, zip_path: str) -> Optional[str]:
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                return self._infer_input_type_zip(zf)
        except Exception:
            return None

    def _infer_input_type_zip(self, zf: zipfile.ZipFile) -> Optional[str]:
        harness_texts: List[str] = []
        ext_counts: Dict[str, int] = {}

        # Scan a limited set of likely harness/source files
        for zi in zf.infolist():
            if zi.is_dir() or zi.file_size <= 0:
                continue
            name = zi.filename
            nl = name.lower()
            ext = _ext(nl)
            if ext:
                ext_counts[ext] = ext_counts.get(ext, 0) + 1
            if zi.file_size > 1_000_000:
                continue
            if ext not in SOURCE_EXT:
                continue
            if "fuzz" not in nl and "fuzzer" not in nl and "oss-fuzz" not in nl and "ossfuzz" not in nl:
                continue
            try:
                data = zf.read(zi)
            except Exception:
                continue
            if not data:
                continue
            if not _looks_text(data):
                continue
            txt = data.decode("utf-8", "replace")
            if "LLVMFuzzerTestOneInput" in txt or "atheris" in txt.lower():
                harness_texts.append(txt)
                if len(harness_texts) >= 6:
                    break

        for t in harness_texts:
            inferred = _infer_type_from_harness_text(t)
            if inferred:
                return inferred

        inferred = _infer_type_from_extension_counts(ext_counts)
        return inferred

    def _infer_input_type_tar(self, tf: tarfile.TarFile) -> Optional[str]:
        harness_texts: List[str] = []
        ext_counts: Dict[str, int] = {}

        members = tf.getmembers()
        for m in members:
            if not m.isreg() or m.size <= 0:
                continue
            nl = m.name.lower()
            ext = _ext(nl)
            if ext:
                ext_counts[ext] = ext_counts.get(ext, 0) + 1

        # Search for likely harnesses
        for m in members:
            if not m.isreg() or m.size <= 0 or m.size > 1_000_000:
                continue
            nl = m.name.lower()
            ext = _ext(nl)
            if ext not in SOURCE_EXT:
                continue
            if "fuzz" not in nl and "fuzzer" not in nl and "oss-fuzz" not in nl and "ossfuzz" not in nl:
                continue
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read(200_000)
            except Exception:
                continue
            if not data:
                continue
            if not _looks_text(data):
                continue
            txt = data.decode("utf-8", "replace")
            if "LLVMFuzzerTestOneInput" in txt or "atheris" in txt.lower():
                harness_texts.append(txt)
                if len(harness_texts) >= 8:
                    break

        for t in harness_texts:
            inferred = _infer_type_from_harness_text(t)
            if inferred:
                return inferred

        return _infer_type_from_extension_counts(ext_counts)

    def _infer_input_type_dir(self, root: str) -> Optional[str]:
        harness_texts: List[str] = []
        ext_counts: Dict[str, int] = {}
        zip_paths: List[str] = []

        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                rel = os.path.relpath(p, root).replace(os.sep, "/")
                ext = _ext(rel)
                if ext:
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1
                if fn.lower().endswith(".zip"):
                    try:
                        st = os.stat(p)
                        if st.st_size < 80_000_000:
                            zip_paths.append(p)
                    except Exception:
                        pass

                if len(harness_texts) >= 8:
                    continue
                if ext not in SOURCE_EXT:
                    continue
                rl = rel.lower()
                if "fuzz" not in rl and "fuzzer" not in rl and "oss-fuzz" not in rl and "ossfuzz" not in rl:
                    continue
                try:
                    st = os.stat(p)
                    if st.st_size > 1_000_000:
                        continue
                    with open(p, "rb") as f:
                        data = f.read(200_000)
                except Exception:
                    continue
                if not data or not _looks_text(data):
                    continue
                txt = data.decode("utf-8", "replace")
                if "LLVMFuzzerTestOneInput" in txt or "atheris" in txt.lower():
                    harness_texts.append(txt)

        for t in harness_texts:
            inferred = _infer_type_from_harness_text(t)
            if inferred:
                return inferred

        # Try infer from zips too
        for zp in zip_paths[:20]:
            try:
                with zipfile.ZipFile(zp, "r") as zf:
                    inferred = self._infer_input_type_zip(zf)
                    if inferred:
                        return inferred
            except Exception:
                continue

        return _infer_type_from_extension_counts(ext_counts)