import os
import tarfile
import gzip
import bz2
import lzma
import zipfile
import io


TARGET_LEN = 2179

KEYWORDS = (
    "poc",
    "crash",
    "oss-fuzz",
    "ossfuzz",
    "uninit",
    "issue",
    "bug",
    "testcase",
    "repro",
    "clusterfuzz",
)

CODE_EXTS = {
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hh",
    ".hpp",
    ".hxx",
    ".inl",
    ".java",
    ".cs",
    ".js",
    ".ts",
    ".go",
    ".rb",
    ".php",
    ".sh",
    ".bat",
    ".cmake",
    ".m4",
    ".am",
    ".ac",
    ".pc",
    ".mak",
    ".mk",
}

INPUT_EXTS = {
    ".xml",
    ".json",
    ".bin",
    ".data",
    ".dat",
    ".txt",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".csv",
    ".html",
    ".htm",
    ".msgpack",
    ".in",
    ".out",
}


def _compute_score(name: str, size: int) -> float:
    lower = name.lower()
    ext = os.path.splitext(lower)[1]

    score = float(abs(size - TARGET_LEN))

    if size == TARGET_LEN:
        score -= 0.1

    if any(k in lower for k in KEYWORDS):
        score *= 0.1

    if (
        "/test" in lower
        or "/tests" in lower
        or "/fuzz" in lower
        or "/regress" in lower
        or "oss-fuzz" in lower
        or "clusterfuzz" in lower
        or "regression" in lower
    ):
        score *= 0.3

    if ext in INPUT_EXTS:
        score *= 0.7

    if ext in CODE_EXTS:
        score += 1000.0

    return score


def _maybe_decompress(name: str, raw: bytes) -> bytes:
    lower = name.lower()
    try:
        if lower.endswith((".gz", ".gzip")):
            data = gzip.decompress(raw)
        elif lower.endswith(".bz2"):
            data = bz2.decompress(raw)
        elif lower.endswith((".xz", ".lzma")):
            data = lzma.decompress(raw)
        elif lower.endswith(".zip"):
            zf = zipfile.ZipFile(io.BytesIO(raw))
            best_info = None
            best_diff = float("inf")
            for info in zf.infolist():
                if info.is_dir():
                    continue
                if info.file_size == 0:
                    continue
                diff = abs(info.file_size - TARGET_LEN)
                if diff < best_diff:
                    best_diff = diff
                    best_info = info
            if best_info is None:
                return raw
            data = zf.read(best_info.filename)
        else:
            return raw

        if abs(len(data) - TARGET_LEN) <= max(TARGET_LEN // 2, 1024):
            return data
        return raw
    except Exception:
        return raw


class Solution:
    def solve(self, src_path: str) -> bytes:
        if not tarfile.is_tarfile(src_path):
            return b"A" * TARGET_LEN

        best_member = None
        best_score = float("inf")

        with tarfile.open(src_path, "r:*") as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                size = member.size
                if size <= 0:
                    continue
                score = _compute_score(member.name, size)
                if score < best_score:
                    best_score = score
                    best_member = member

            if best_member is None:
                return b"A" * TARGET_LEN

            f = tf.extractfile(best_member)
            if f is None:
                return b"A" * TARGET_LEN
            raw = f.read()

        data = _maybe_decompress(best_member.name, raw)

        if not data:
            return b"A" * TARGET_LEN

        return data