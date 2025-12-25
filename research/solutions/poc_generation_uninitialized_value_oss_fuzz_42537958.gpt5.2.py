import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


def _read_text_file(path: str, max_bytes: int = 2_000_000) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            data = f.read(max_bytes)
        return data.decode("utf-8", "replace")
    except Exception:
        return None


def _iter_source_files_from_dir(root: str) -> Iterable[Tuple[str, str]]:
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            lfn = fn.lower()
            if not (lfn.endswith(".c") or lfn.endswith(".cc") or lfn.endswith(".cpp") or lfn.endswith(".cxx") or lfn.endswith(".h") or lfn.endswith(".hpp")):
                continue
            p = os.path.join(dirpath, fn)
            txt = _read_text_file(p)
            if txt is None:
                continue
            yield p, txt


def _iter_source_files_from_tar(tar_path: str) -> Iterable[Tuple[str, str]]:
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                lname = name.lower()
                if not (lname.endswith(".c") or lname.endswith(".cc") or lname.endswith(".cpp") or lname.endswith(".cxx") or lname.endswith(".h") or lname.endswith(".hpp")):
                    continue
                if m.size > 2_000_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                    txt = data.decode("utf-8", "replace")
                except Exception:
                    continue
                yield name, txt
    except Exception:
        return


def _strip_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//[^\n]*", "", s)
    return s


def _extract_function_body(text: str, func_name: str = "LLVMFuzzerTestOneInput") -> Optional[str]:
    idx = text.find(func_name)
    if idx < 0:
        return None
    lb = text.find("{", idx)
    if lb < 0:
        return None
    i = lb + 1
    depth = 1
    n = len(text)
    in_str = False
    str_ch = ""
    escape = False
    while i < n:
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == str_ch:
                in_str = False
        else:
            if ch == '"' or ch == "'":
                in_str = True
                str_ch = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[lb + 1 : i]
        i += 1
    return None


def _type_size(type_name: str) -> int:
    t = type_name.strip()
    t = re.sub(r"\bconst\b", "", t).strip()
    t = re.sub(r"\bvolatile\b", "", t).strip()
    t = t.replace("std::", "").strip()
    t = re.sub(r"\s+", " ", t)

    mapping: Dict[str, int] = {
        "bool": 1,
        "char": 1,
        "signed char": 1,
        "unsigned char": 1,
        "int8_t": 1,
        "uint8_t": 1,
        "short": 2,
        "short int": 2,
        "unsigned short": 2,
        "unsigned short int": 2,
        "int16_t": 2,
        "uint16_t": 2,
        "int": 4,
        "unsigned": 4,
        "unsigned int": 4,
        "long": 8,
        "long int": 8,
        "unsigned long": 8,
        "unsigned long int": 8,
        "long long": 8,
        "long long int": 8,
        "unsigned long long": 8,
        "unsigned long long int": 8,
        "int32_t": 4,
        "uint32_t": 4,
        "int64_t": 8,
        "uint64_t": 8,
        "size_t": 8,
        "ssize_t": 8,
        "ptrdiff_t": 8,
    }
    if t in mapping:
        return mapping[t]

    t2 = t.replace(" ", "")
    mapping2: Dict[str, int] = {
        "uint8_t": 1,
        "int8_t": 1,
        "uint16_t": 2,
        "int16_t": 2,
        "uint32_t": 4,
        "int32_t": 4,
        "uint64_t": 8,
        "int64_t": 8,
        "size_t": 8,
    }
    if t2 in mapping2:
        return mapping2[t2]
    return 4


def _analyze_fixed_offset(text: str) -> Optional[int]:
    body = _extract_function_body(text) or text
    body_nc = _strip_comments(body)

    assign_pat1 = re.compile(r"\b(jpeg|jpg)\w*\s*=\s*data\s*\+\s*(\d+)\b")
    assign_pat2 = re.compile(r"\b(jpeg|jpg)\w*\s*=\s*&\s*data\s*\[\s*(\d+)\s*\]")
    m = assign_pat1.search(body_nc)
    if m:
        try:
            return int(m.group(2))
        except Exception:
            pass
    m = assign_pat2.search(body_nc)
    if m:
        try:
            return int(m.group(2))
        except Exception:
            pass

    for fn in (
        "tj3DecompressHeader",
        "tjDecompressHeader3",
        "tjDecompressHeader2",
        "tj3Decompress8",
        "tjDecompress2",
        "tj3Transform",
        "tjTransform",
        "jpeg_mem_src",
    ):
        idx = body_nc.find(fn + "(")
        if idx >= 0:
            seg = body_nc[idx : idx + 400]
            m1 = re.search(r"\bdata\s*\+\s*(\d+)\b", seg)
            if m1:
                try:
                    return int(m1.group(1))
                except Exception:
                    pass
            m2 = re.search(r"&\s*data\s*\[\s*(\d+)\s*\]", seg)
            if m2:
                try:
                    return int(m2.group(1))
                except Exception:
                    pass

    return None


def _analyze_fdp_prefix(text: str) -> Optional[int]:
    body = _extract_function_body(text)
    if body is None:
        return None
    body = _strip_comments(body)

    m = re.search(r"\bConsumeRemainingBytes(?:AsString)?\b", body)
    if not m:
        return None
    remaining_pos = m.start()

    prefix_text = body[:remaining_pos]

    consume_regex = re.compile(
        r"\bConsumeBool\s*\(|\bConsumeIntegralInRange\s*<\s*([^>]+?)\s*>\s*\(|\bConsumeIntegral\s*<\s*([^>]+?)\s*>\s*\(",
        flags=re.S,
    )
    matches = [(mm.start(), mm.group(1), mm.group(2), mm.group(0)) for mm in consume_regex.finditer(prefix_text)]
    if not matches:
        return 0

    depth = 0
    total = 0
    matches.sort(key=lambda x: x[0])
    mi = 0
    next_pos = matches[mi][0]

    i = 0
    n = len(prefix_text)
    in_str = False
    str_ch = ""
    escape = False
    while i < n:
        if i == next_pos:
            if depth == 0:
                _, g1, g2, g0 = matches[mi]
                if "ConsumeBool" in g0:
                    total += 1
                else:
                    tname = g1 if g1 is not None else g2
                    total += _type_size(tname or "int")
            mi += 1
            next_pos = matches[mi][0] if mi < len(matches) else None
        ch = prefix_text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == str_ch:
                in_str = False
        else:
            if ch == '"' or ch == "'":
                in_str = True
                str_ch = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth < 0:
                    depth = 0
        i += 1
        if next_pos is None and i > next_pos if next_pos is not None else False:
            break

    return total


def _find_fuzzer_sources(src_path: str) -> List[Tuple[str, str]]:
    res: List[Tuple[str, str]] = []
    if os.path.isdir(src_path):
        for name, txt in _iter_source_files_from_dir(src_path):
            if "LLVMFuzzerTestOneInput" in txt:
                res.append((name, txt))
        return res
    if os.path.isfile(src_path):
        for name, txt in _iter_source_files_from_tar(src_path):
            if "LLVMFuzzerTestOneInput" in txt:
                res.append((name, txt))
        return res
    return res


def _build_minimal_gray_jpeg(w: int = 16, h: int = 8) -> bytes:
    # Standard luminance quantization table (zig-zag order)
    qtbl = bytes([
        16, 11, 10, 16, 24, 40, 51, 61,
        12, 12, 14, 19, 26, 58, 60, 55,
        14, 13, 16, 24, 40, 57, 69, 56,
        14, 17, 22, 29, 51, 87, 80, 62,
        18, 22, 37, 56, 68, 109, 103, 77,
        24, 35, 55, 64, 81, 104, 113, 92,
        49, 64, 78, 87, 103, 121, 120, 101,
        72, 92, 95, 98, 112, 100, 103, 99
    ])

    # Standard Huffman tables (luminance)
    dc_bits = bytes([0x00, 0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    dc_vals = bytes([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])

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

    def seg(marker: bytes, payload: bytes) -> bytes:
        ln = len(payload) + 2
        return marker + bytes([(ln >> 8) & 0xFF, ln & 0xFF]) + payload

    out = bytearray()
    out += b"\xFF\xD8"  # SOI

    # APP0 JFIF
    app0 = b"JFIF\x00" + bytes([0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00])
    out += seg(b"\xFF\xE0", app0)

    # DQT (one table, 8-bit, id 0)
    out += seg(b"\xFF\xDB", bytes([0x00]) + qtbl)

    # SOF0 (baseline, 1 component)
    sof0 = bytearray()
    sof0 += bytes([0x08])  # precision
    sof0 += bytes([(h >> 8) & 0xFF, h & 0xFF, (w >> 8) & 0xFF, w & 0xFF])
    sof0 += bytes([0x01])  # components
    sof0 += bytes([0x01, 0x11, 0x00])  # id=1, samp=1x1, qtbl=0
    out += seg(b"\xFF\xC0", bytes(sof0))

    # DHT DC (class 0, id 0)
    out += seg(b"\xFF\xC4", bytes([0x00]) + dc_bits + dc_vals)
    # DHT AC (class 1, id 0)
    out += seg(b"\xFF\xC4", bytes([0x10]) + ac_bits + ac_vals)

    # SOS
    sos = bytes([0x01, 0x01, 0x00, 0x00, 0x3F, 0x00])
    out += seg(b"\xFF\xDA", sos)

    # Entropy-coded data for constant 128 image => all-zero DCT coefficients.
    # For each 8x8 block: DC diff category 0 => "00"; AC all zero => EOB "1010" => 6 bits/block.
    import math
    blocks = int(math.ceil(w / 8.0) * math.ceil(h / 8.0))

    def emit_bits(bitbuf: int, nbits: int, acc: int, accbits: int, dst: bytearray) -> Tuple[int, int]:
        acc = (acc << nbits) | (bitbuf & ((1 << nbits) - 1))
        accbits += nbits
        while accbits >= 8:
            accbits -= 8
            b = (acc >> accbits) & 0xFF
            dst.append(b)
            if b == 0xFF:
                dst.append(0x00)
            acc &= (1 << accbits) - 1 if accbits > 0 else 0
        return acc, accbits

    entropy = bytearray()
    acc = 0
    accbits = 0
    for _ in range(blocks):
        acc, accbits = emit_bits(0b00, 2, acc, accbits, entropy)      # DC category 0
        acc, accbits = emit_bits(0b1010, 4, acc, accbits, entropy)    # EOB
    if accbits:
        pad = (1 << (8 - accbits)) - 1  # pad with ones
        acc, accbits = emit_bits(pad, 8 - accbits, acc, accbits, entropy)

    out += entropy
    out += b"\xFF\xD9"  # EOI
    return bytes(out)


class Solution:
    def solve(self, src_path: str) -> bytes:
        fuzzers = _find_fuzzer_sources(src_path)
        chosen_text = None
        if fuzzers:
            fuzzers.sort(key=lambda x: (0 if "tj3" in x[0].lower() or "turbo" in x[0].lower() else 1, len(x[1])))
            chosen_text = fuzzers[0][1]

        jpeg = _build_minimal_gray_jpeg(16, 8)

        offset = 0
        if chosen_text is not None:
            off = _analyze_fixed_offset(chosen_text)
            if off is not None and 0 <= off <= 4096:
                offset = off
            else:
                pfx = _analyze_fdp_prefix(chosen_text)
                if pfx is not None and 0 <= pfx <= 4096:
                    offset = pfx

        if offset <= 0:
            return jpeg
        return (b"\x00" * offset) + jpeg