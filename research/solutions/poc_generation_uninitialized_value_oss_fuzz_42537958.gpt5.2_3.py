import base64
import io
import os
import re
import tarfile
from typing import Optional, Tuple


_BASE_JPEG_B64 = (
    b"/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3+iiigD//2Q=="
)


def _iter_fuzzer_sources_from_tar(src_path: str, max_bytes: int = 1_500_000):
    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name.lower()
                if not (name.endswith(".c") or name.endswith(".cc") or name.endswith(".cpp")):
                    continue
                if "fuzz" not in name and "fuzzer" not in name:
                    continue
                if m.size <= 0 or m.size > max_bytes:
                    continue
                f = tf.extractfile(m)
                if not f:
                    continue
                try:
                    data = f.read()
                finally:
                    f.close()
                try:
                    text = data.decode("utf-8", errors="ignore")
                except Exception:
                    continue
                if "LLVMFuzzerTestOneInput" not in text:
                    continue
                yield m.name, text
    except Exception:
        return


def _pick_relevant_fuzzer_text(src_path: str) -> Optional[Tuple[str, str]]:
    best = None
    best_score = -1
    for name, text in _iter_fuzzer_sources_from_tar(src_path):
        score = 0
        lname = name.lower()
        if "tj3" in lname or "turbojpeg" in lname:
            score += 5
        if "transform" in lname:
            score += 3
        if "compress" in lname:
            score += 2
        if "decompress" in lname:
            score += 2

        t = text
        if "tj3" in t:
            score += 4
        if "tj3Transform" in t or "tjTransform" in t:
            score += 4
        if "tj3Compress" in t or "tjCompress" in t:
            score += 3
        if "FuzzedDataProvider" in t:
            score += 1
        if "ConsumeRemainingBytes" in t:
            score += 1

        if score > best_score:
            best_score = score
            best = (name, text)
    return best


_TYPE_SIZES = {
    "uint8_t": 1,
    "int8_t": 1,
    "unsigned char": 1,
    "char": 1,
    "bool": 1,
    "uint16_t": 2,
    "int16_t": 2,
    "unsigned short": 2,
    "short": 2,
    "uint32_t": 4,
    "int32_t": 4,
    "unsigned int": 4,
    "int": 4,
    "uint64_t": 8,
    "int64_t": 8,
    "unsigned long long": 8,
    "long long": 8,
    "size_t": 8,
    "ssize_t": 8,
    "unsigned long": 8,
    "long": 8,
}


def _estimate_prefix_len_from_fdp(text: str) -> int:
    m = re.search(r"LLVMFuzzerTestOneInput\s*\([^)]*\)\s*\{", text)
    if not m:
        return 0
    start = m.end()
    end = text.find("ConsumeRemainingBytes", start)
    if end < 0:
        return 0
    pre = text[start:end]

    prefix = 0

    prefix += len(re.findall(r"\bConsumeBool\s*\(", pre))

    for tm in re.finditer(r"\bConsumeIntegral(?:InRange)?\s*<\s*([^>\s]+)\s*>\s*\(", pre):
        typ = tm.group(1).strip()
        prefix += _TYPE_SIZES.get(typ, 4)

    for tm in re.finditer(r"\bConsumeEnum\s*<\s*([^>\s]+)\s*>\s*\(", pre):
        _ = tm.group(1).strip()
        prefix += 4

    for tm in re.finditer(r"\bConsumeBytes(?:AsString)?\s*<[^>]*>\s*\(\s*(\d+)\s*\)", pre):
        prefix += int(tm.group(1))

    for tm in re.finditer(r"\bConsumeBytes(?:AsString)?\s*\(\s*(\d+)\s*\)", pre):
        prefix += int(tm.group(1))

    if prefix < 0:
        prefix = 0
    if prefix > 4096:
        prefix = 4096
    return prefix


def _estimate_prefix_len_from_data_offset(text: str) -> int:
    candidates = []
    for line in text.splitlines():
        if ("tj" not in line) or ("data" not in line):
            continue
        if "data +" in line:
            for m in re.finditer(r"\bdata\s*\+\s*(\d+)\b", line):
                try:
                    n = int(m.group(1))
                except Exception:
                    continue
                if 0 <= n <= 4096:
                    candidates.append(n)
        if "&data[" in line:
            for m in re.finditer(r"&\s*data\s*\[\s*(\d+)\s*\]", line):
                try:
                    n = int(m.group(1))
                except Exception:
                    continue
                if 0 <= n <= 4096:
                    candidates.append(n)
    if not candidates:
        return 0
    return min(candidates)


def _should_prepend_prefix(text: str) -> Tuple[bool, int]:
    if not text:
        return False, 0

    direct_use = False
    for pat in (
        r"\btj3\w*\s*Transform\w*\s*\([^;]*\bdata\b",
        r"\btj3\w*\s*Decompress\w*\s*\([^;]*\bdata\b",
        r"\btj3\w*\s*DecompressHeader\w*\s*\([^;]*\bdata\b",
        r"\btj\w*\s*Transform\w*\s*\([^;]*\bdata\b",
        r"\btj\w*\s*Decompress\w*\s*\([^;]*\bdata\b",
        r"\btj\w*\s*DecompressHeader\w*\s*\([^;]*\bdata\b",
    ):
        if re.search(pat, text, flags=re.IGNORECASE | re.DOTALL):
            direct_use = True
            break

    off_prefix = _estimate_prefix_len_from_data_offset(text)
    if off_prefix > 0:
        return True, off_prefix

    if direct_use:
        return False, 0

    if "FuzzedDataProvider" in text and "ConsumeRemainingBytes" in text:
        est = _estimate_prefix_len_from_fdp(text)
        if est > 0:
            return True, est

    return False, 0


def _pattern_bytes(n: int, seed: int = 0x42) -> bytes:
    if n <= 0:
        return b""
    b = bytearray(n)
    x = seed & 0xFF
    for i in range(n):
        x = (x * 131 + 17) & 0xFF
        b[i] = x
    return bytes(b)


class Solution:
    def solve(self, src_path: str) -> bytes:
        base = base64.b64decode(_BASE_JPEG_B64)
        if len(base) < 4 or base[:2] != b"\xff\xd8":
            base = b"\xff\xd8\xff\xd9"

        fuzzer = _pick_relevant_fuzzer_text(src_path) if src_path and os.path.exists(src_path) else None
        prefix_len = 0
        if fuzzer:
            _, text = fuzzer
            need_prefix, prefix_len = _should_prepend_prefix(text)
            if not need_prefix:
                prefix_len = 0

        total_target = 2048
        min_needed = prefix_len + len(base) + 64
        if total_target < min_needed:
            total_target = min_needed
        if total_target > 16384:
            total_target = 16384

        prefix = b"\x00" * prefix_len
        pad_len = total_target - prefix_len - len(base)
        pad = _pattern_bytes(pad_len, seed=0x7B)

        return prefix + base + pad