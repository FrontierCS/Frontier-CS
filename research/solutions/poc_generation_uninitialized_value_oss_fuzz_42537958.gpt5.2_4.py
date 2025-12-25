import os
import re
import tarfile
import zipfile
import base64
import tempfile
from typing import Optional, Tuple, List


_MIN_JPEG_B64 = (
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRof"
    "Hh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwh"
    "MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAAR"
    "CAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAA"
    "AgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkK"
    "FhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWG"
    "h4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl"
    "5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREA"
    "AgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYk"
    "NOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOE"
    "hYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk"
    "5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD+f+iiigD/2Q=="
)
MIN_JPEG = base64.b64decode(_MIN_JPEG_B64)


def _safe_extract_tar(tar_path: str, dst_dir: str) -> None:
    def is_within_directory(directory: str, target: str) -> bool:
        abs_directory = os.path.abspath(directory)
        abs_target = os.path.abspath(target)
        return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])

    with tarfile.open(tar_path, "r:*") as tf:
        for m in tf.getmembers():
            name = m.name
            if not name or name.startswith("/") or name.startswith("\\"):
                continue
            target_path = os.path.join(dst_dir, name)
            if not is_within_directory(dst_dir, target_path):
                continue
            try:
                tf.extract(m, dst_dir)
            except Exception:
                pass


def _read_file_bytes(path: str, max_bytes: int = 4 * 1024 * 1024) -> Optional[bytes]:
    try:
        st = os.stat(path)
        if st.st_size <= 0 or st.st_size > max_bytes:
            return None
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None


def _read_file_text(path: str, max_bytes: int = 2 * 1024 * 1024) -> Optional[str]:
    b = _read_file_bytes(path, max_bytes=max_bytes)
    if b is None:
        return None
    try:
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return None


_TYPE_SIZES = {
    "bool": 1,
    "char": 1,
    "signedchar": 1,
    "unsignedchar": 1,
    "int8_t": 1,
    "uint8_t": 1,
    "int16_t": 2,
    "uint16_t": 2,
    "short": 2,
    "unsignedshort": 2,
    "int": 4,
    "unsigned": 4,
    "unsignedint": 4,
    "int32_t": 4,
    "uint32_t": 4,
    "float": 4,
    "long": 8,
    "unsignedlong": 8,
    "int64_t": 8,
    "uint64_t": 8,
    "longlong": 8,
    "unsignedlonglong": 8,
    "double": 8,
    "size_t": 8,
    "ssize_t": 8,
    "uintptr_t": 8,
    "intptr_t": 8,
}


def _normalize_type_name(t: str) -> str:
    t = t.strip()
    t = re.sub(r"\b(const|volatile)\b", "", t)
    t = t.replace("std::", "")
    t = t.replace("::", "")
    t = t.replace("*", "")
    t = t.replace("&", "")
    t = re.sub(r"\s+", " ", t).strip()
    t = t.replace(" ", "")
    return t


def _sizeof_template_type(t: str) -> int:
    nt = _normalize_type_name(t)
    if nt in _TYPE_SIZES:
        return _TYPE_SIZES[nt]
    if nt.startswith("unsigned") and nt != "unsigned":
        if nt in _TYPE_SIZES:
            return _TYPE_SIZES[nt]
    return 4


def _extract_fuzzer_function(content: str) -> Optional[str]:
    idx = content.find("LLVMFuzzerTestOneInput")
    if idx < 0:
        return None
    brace_start = content.find("{", idx)
    if brace_start < 0:
        return None
    i = brace_start
    depth = 0
    while i < len(content):
        c = content[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return content[brace_start : i + 1]
        i += 1
    return None


def _count_prefix_before_consume_remaining(func_src: str) -> Optional[int]:
    pos = func_src.find("ConsumeRemainingBytes")
    if pos < 0:
        return None
    prefix = func_src[:pos]

    total = 0

    total += len(re.findall(r"\.ConsumeBool\s*\(", prefix)) * 1
    total += len(re.findall(r"\.ConsumeProbability\s*\(", prefix)) * 4

    for m in re.finditer(r"\.ConsumeIntegralInRange\s*<\s*([^>]+)\s*>\s*\(", prefix):
        total += _sizeof_template_type(m.group(1))
    for m in re.finditer(r"\.ConsumeIntegral\s*<\s*([^>]+)\s*>\s*\(", prefix):
        total += _sizeof_template_type(m.group(1))
    for m in re.finditer(r"\.ConsumeEnum\s*<\s*([^>]+)\s*>\s*\(", prefix):
        # Assume underlying type is 4 bytes (common)
        total += 4
    for m in re.finditer(r"\.ConsumeFloatingPointInRange\s*<\s*([^>]+)\s*>\s*\(", prefix):
        total += _sizeof_template_type(m.group(1))
    for m in re.finditer(r"\.ConsumeFloatingPoint\s*<\s*([^>]+)\s*>\s*\(", prefix):
        total += _sizeof_template_type(m.group(1))

    if total < 0 or total > 8192:
        return None
    return total


def _score_fuzzer_source(txt: str) -> int:
    s = 0
    low = txt.lower()
    if "llvMfuzzertestoneinput".lower() in low:
        s += 5
    if "zero_buffers" in low:
        s += 60
    if "tj3" in low:
        s += 40
    if "turbojpeg" in low or "turbojpeg.h" in low:
        s += 25
    if "tj3transform" in low or "tjtransform" in low:
        s += 20
    if "tj3compress" in low or "tjcompress" in low:
        s += 20
    if "fuzzeddataprovider" in low:
        s += 10
    if "consumeRemainingBytes".lower() in low:
        s += 5
    return s


def _find_best_fuzzer_source(root: str) -> Optional[Tuple[str, str]]:
    best = None
    best_score = -1
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not (fn.endswith(".c") or fn.endswith(".cc") or fn.endswith(".cpp") or fn.endswith(".cxx")):
                continue
            path = os.path.join(dirpath, fn)
            txt = _read_file_text(path, max_bytes=2 * 1024 * 1024)
            if not txt or "LLVMFuzzerTestOneInput" not in txt:
                continue
            sc = _score_fuzzer_source(txt)
            if sc > best_score:
                best_score = sc
                best = (path, txt)
    return best


def _iter_seed_candidates(root: str) -> List[Tuple[str, bool]]:
    candidates: List[Tuple[str, bool]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        lowdir = dirpath.lower()
        is_seed_dir = any(k in lowdir for k in ("corpus", "seed", "seeds", "testdata", "samples", "sample", "regression"))
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            lowfn = fn.lower()
            if lowfn.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".md", ".txt", ".rst", ".html", ".cmake", ".py", ".sh")):
                continue
            is_zip = lowfn.endswith(".zip")
            if is_seed_dir or is_zip or lowfn.endswith((".jpg", ".jpeg", ".jfif")):
                candidates.append((path, is_zip))
    return candidates


def _choose_seed_direct_jpeg(root: str) -> Optional[bytes]:
    best_bytes = None
    best_len = None
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            lowfn = fn.lower()
            if not lowfn.endswith((".jpg", ".jpeg", ".jfif")):
                continue
            path = os.path.join(dirpath, fn)
            b = _read_file_bytes(path, max_bytes=2 * 1024 * 1024)
            if not b or len(b) < 20:
                continue
            if not (len(b) >= 2 and b[0] == 0xFF and b[1] == 0xD8):
                continue
            if best_len is None or len(b) < best_len:
                best_len = len(b)
                best_bytes = b
    return best_bytes


def _choose_seed_from_corpus_any(root: str) -> Optional[bytes]:
    candidates = _iter_seed_candidates(root)

    # Prefer seed_corpus zip archives
    zip_paths = [p for p, is_zip in candidates if is_zip and ("seed_corpus" in os.path.basename(p).lower() or "corpus" in os.path.basename(p).lower())]
    zip_paths += [p for p, is_zip in candidates if is_zip and p not in zip_paths]

    best = None
    best_len = None

    def consider(blob: bytes) -> None:
        nonlocal best, best_len
        if not blob or len(blob) < 2:
            return
        if best_len is None or len(blob) < best_len:
            best = blob
            best_len = len(blob)

    for zp in zip_paths:
        try:
            with zipfile.ZipFile(zp, "r") as zf:
                infos = [i for i in zf.infolist() if not i.is_dir() and i.file_size > 0 and i.file_size <= 2 * 1024 * 1024]
                if not infos:
                    continue
                # Prefer JPEG-looking entries if any
                jpeg_infos = [i for i in infos if i.file_size >= 2]
                jpeg_infos_sorted = sorted(jpeg_infos, key=lambda i: i.file_size)
                for info in jpeg_infos_sorted[:64]:
                    try:
                        data = zf.read(info)
                        if len(data) >= 2 and data[0] == 0xFF and data[1] == 0xD8:
                            consider(data)
                            break
                    except Exception:
                        continue
                if best is not None:
                    return best
                # Otherwise smallest entry
                info = min(infos, key=lambda i: i.file_size)
                try:
                    data = zf.read(info)
                    consider(data)
                except Exception:
                    pass
        except Exception:
            continue
        if best is not None:
            return best

    # Non-zip candidates
    files = [p for p, is_zip in candidates if not is_zip]
    # Prefer JPEG magic among these
    jpeg_files = []
    other_files = []
    for p in files:
        b = _read_file_bytes(p, max_bytes=2 * 1024 * 1024)
        if not b:
            continue
        if len(b) >= 2 and b[0] == 0xFF and b[1] == 0xD8:
            jpeg_files.append((p, b))
        else:
            other_files.append((p, b))

    if jpeg_files:
        jpeg_files.sort(key=lambda x: len(x[1]))
        return jpeg_files[0][1]
    if other_files:
        other_files.sort(key=lambda x: len(x[1]))
        return other_files[0][1]
    return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            return self._solve_from_root(src_path)

        with tempfile.TemporaryDirectory() as td:
            try:
                _safe_extract_tar(src_path, td)
            except Exception:
                pass
            return self._solve_from_root(td)

    def _solve_from_root(self, root: str) -> bytes:
        fuzzer = _find_best_fuzzer_source(root)
        mode = "unknown"
        prefix_len = 0

        if fuzzer is not None:
            _, txt = fuzzer
            func = _extract_fuzzer_function(txt) or ""
            if "ConsumeRemainingBytes" in func:
                mode = "fdp_remaining"
                pl = _count_prefix_before_consume_remaining(func)
                if pl is not None:
                    prefix_len = pl
                else:
                    prefix_len = 0
            else:
                mode = "direct"

        if mode == "direct":
            seed = _choose_seed_direct_jpeg(root)
            if seed is not None:
                return seed
            return MIN_JPEG

        if mode == "fdp_remaining":
            seed = _choose_seed_from_corpus_any(root)
            if seed is not None:
                return seed
            if prefix_len > 0:
                return (b"\x00" * prefix_len) + MIN_JPEG
            return MIN_JPEG

        seed = _choose_seed_from_corpus_any(root)
        if seed is not None:
            return seed
        return MIN_JPEG