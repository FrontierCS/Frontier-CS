import os
import re
import tarfile
import struct
from typing import Optional, Tuple, List


def _jpeg_constant_gray_baseline_444(width: int = 256, height: int = 256) -> bytes:
    if width <= 0 or height <= 0 or (width % 8) != 0 or (height % 8) != 0:
        raise ValueError("width and height must be positive and multiples of 8")

    # Standard quantization tables in zigzag order (Annex K)
    lum_q = bytes([
        16, 11, 10, 16, 24, 40, 51, 61,
        12, 12, 14, 19, 26, 58, 60, 55,
        14, 13, 16, 24, 40, 57, 69, 56,
        14, 17, 22, 29, 51, 87, 80, 62,
        18, 22, 37, 56, 68, 109, 103, 77,
        24, 35, 55, 64, 81, 104, 113, 92,
        49, 64, 78, 87, 103, 121, 120, 101,
        72, 92, 95, 98, 112, 100, 103, 99
    ])
    chr_q = bytes([
        17, 18, 24, 47, 99, 99, 99, 99,
        18, 21, 26, 66, 99, 99, 99, 99,
        24, 26, 56, 99, 99, 99, 99, 99,
        47, 66, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99,
        99, 99, 99, 99, 99, 99, 99, 99
    ])

    # Standard Huffman tables (Annex K)
    bits_dc_lum = bytes([0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0])
    val_dc_lum = bytes(list(range(12)))

    bits_dc_chr = bytes([0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0])
    val_dc_chr = bytes(list(range(12)))

    bits_ac_lum = bytes([0x00, 0x02, 0x01, 0x03, 0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D])
    val_ac_lum = bytes([
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

    bits_ac_chr = bytes([0x00, 0x02, 0x01, 0x02, 0x04, 0x04, 0x03, 0x04, 0x07, 0x05, 0x04, 0x04, 0x00, 0x01, 0x02, 0x77])
    val_ac_chr = bytes([
        0x00, 0x01, 0x02, 0x03, 0x11, 0x04, 0x05, 0x21, 0x31, 0x06, 0x12, 0x41, 0x51, 0x07, 0x61, 0x71,
        0x13, 0x22, 0x32, 0x81, 0x08, 0x14, 0x42, 0x91, 0xA1, 0xB1, 0xC1, 0x09, 0x23, 0x33, 0x52, 0xF0,
        0x15, 0x62, 0x72, 0xD1, 0x0A, 0x16, 0x24, 0x34, 0xE1, 0x25, 0xF1, 0x17, 0x18, 0x19, 0x1A, 0x26,
        0x27, 0x28, 0x29, 0x2A, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48,
        0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68,
        0x69, 0x6A, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7A, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87,
        0x88, 0x89, 0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3, 0xA4, 0xA5,
        0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3,
        0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA,
        0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8,
        0xF9, 0xFA
    ])

    def seg(marker: int, payload: bytes) -> bytes:
        return b"\xFF" + bytes([marker]) + struct.pack(">H", len(payload) + 2) + payload

    # APP0 JFIF
    app0 = seg(0xE0, b"JFIF\x00" + bytes([1, 1, 0]) + struct.pack(">HH", 1, 1) + bytes([0, 0]))

    # DQT (two tables)
    dqt = seg(0xDB, bytes([0x00]) + lum_q + bytes([0x01]) + chr_q)

    # SOF0
    sof0_payload = bytes([8]) + struct.pack(">HH", height, width) + bytes([3])
    sof0_payload += bytes([1, 0x11, 0])  # Y, 1x1, QT0
    sof0_payload += bytes([2, 0x11, 1])  # Cb, 1x1, QT1
    sof0_payload += bytes([3, 0x11, 1])  # Cr, 1x1, QT1
    sof0 = seg(0xC0, sof0_payload)

    # DHT (4 tables)
    dht_payload = bytearray()
    dht_payload += bytes([0x00]) + bits_dc_lum + val_dc_lum  # DC, table 0
    dht_payload += bytes([0x10]) + bits_ac_lum + val_ac_lum  # AC, table 0
    dht_payload += bytes([0x01]) + bits_dc_chr + val_dc_chr  # DC, table 1
    dht_payload += bytes([0x11]) + bits_ac_chr + val_ac_chr  # AC, table 1
    dht = seg(0xC4, bytes(dht_payload))

    # SOS
    sos_payload = bytes([3])
    sos_payload += bytes([1, 0x00])  # Y: DC0/AC0
    sos_payload += bytes([2, 0x11])  # Cb: DC1/AC1
    sos_payload += bytes([3, 0x11])  # Cr: DC1/AC1
    sos_payload += bytes([0, 63, 0])
    sos = seg(0xDA, sos_payload)

    # Scan data: all coefficients 0 => DC category 0; AC EOB
    # Huffman codes needed:
    # Y DC (cat 0): 00 (len 2)
    # Y AC EOB: 1010 (len 4)
    # C DC (cat 0): 00 (len 2)
    # C AC EOB: 00 (len 2)
    y_dc_code, y_dc_len = 0b00, 2
    y_eob_code, y_eob_len = 0b1010, 4
    c_dc_code, c_dc_len = 0b00, 2
    c_eob_code, c_eob_len = 0b00, 2

    mcu_count = (width // 8) * (height // 8)

    out = bytearray()
    bit_buf = 0
    bit_cnt = 0

    def put_bits(code: int, length: int) -> None:
        nonlocal bit_buf, bit_cnt, out
        bit_buf = (bit_buf << length) | (code & ((1 << length) - 1))
        bit_cnt += length
        while bit_cnt >= 8:
            byte = (bit_buf >> (bit_cnt - 8)) & 0xFF
            out.append(byte)
            if byte == 0xFF:
                out.append(0x00)
            bit_cnt -= 8
            bit_buf &= (1 << bit_cnt) - 1 if bit_cnt > 0 else 0

    for _ in range(mcu_count):
        put_bits(y_dc_code, y_dc_len)
        put_bits(y_eob_code, y_eob_len)
        put_bits(c_dc_code, c_dc_len)
        put_bits(c_eob_code, c_eob_len)
        put_bits(c_dc_code, c_dc_len)
        put_bits(c_eob_code, c_eob_len)

    if bit_cnt > 0:
        pad = (1 << (8 - bit_cnt)) - 1
        byte = ((bit_buf << (8 - bit_cnt)) & 0xFF) | pad
        out.append(byte)
        if byte == 0xFF:
            out.append(0x00)

    scan = bytes(out)

    # Assemble file
    soi = b"\xFF\xD8"
    eoi = b"\xFF\xD9"
    return soi + app0 + dqt + sof0 + dht + sos + scan + eoi


def _scan_tar_for_fuzzer_hint(src_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (best_file_name, content) for a likely fuzzer source.
    """
    if not os.path.exists(src_path):
        return None, None

    best_name = None
    best_content = None
    best_score = -1

    try:
        with tarfile.open(src_path, "r:*") as tf:
            members = tf.getmembers()
            for m in members:
                if not m.isfile():
                    continue
                name = m.name
                low = name.lower()
                if not (low.endswith(".c") or low.endswith(".cc") or low.endswith(".cpp") or low.endswith(".cxx")):
                    continue
                if m.size <= 0 or m.size > 5_000_000:
                    continue
                f = tf.extractfile(m)
                if f is None:
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

                score = 0
                # Prefer files that mention tj3 / turbojpeg operations
                for kw in (
                    "tj3Transform", "tjTransform", "tj3Compress", "tjCompress", "tj3Decompress", "tjDecompress",
                    "DecompressHeader", "tj3Alloc", "tjAlloc", "turbojpeg", "TurboJPEG", "FuzzedDataProvider"
                ):
                    score += text.count(kw) * 10
                if "/fuzz" in low or low.startswith("fuzz/") or "/oss-fuzz" in low:
                    score += 50
                if score > best_score:
                    best_score = score
                    best_name = name
                    best_content = text
    except Exception:
        return None, None

    return best_name, best_content


_TYPE_SIZES = {
    "uint8_t": 1, "int8_t": 1, "unsigned char": 1, "signed char": 1, "char": 1, "bool": 1,
    "uint16_t": 2, "int16_t": 2, "unsigned short": 2, "short": 2,
    "uint32_t": 4, "int32_t": 4, "unsigned int": 4, "int": 4, "unsigned": 4, "float": 4,
    "uint64_t": 8, "int64_t": 8, "unsigned long long": 8, "long long": 8, "double": 8,
    "size_t": 8, "ssize_t": 8
}


def _normalize_type(t: str) -> str:
    t = t.strip()
    t = re.sub(r"\s+", " ", t)
    t = t.replace("std::", "")
    t = t.replace("const ", "")
    t = t.replace("&", "").replace("*", "").strip()
    return t


def _estimate_fdp_prefix_len(content: str) -> int:
    idx = content.find("ConsumeRemainingBytes")
    if idx < 0:
        return 0
    prefix = content[:idx]
    total = 0

    for m in re.finditer(r"ConsumeBool\s*\(", prefix):
        total += 1

    for m in re.finditer(r"ConsumeIntegral(InRange)?\s*<\s*([^>]+)\s*>", prefix):
        t = _normalize_type(m.group(2))
        total += _TYPE_SIZES.get(t, 4)

    for m in re.finditer(r"ConsumeFloatingPoint(InRange)?\s*<\s*([^>]+)\s*>", prefix):
        t = _normalize_type(m.group(2))
        total += _TYPE_SIZES.get(t, 8)

    # Constant ConsumeBytes<...>(N)
    for m in re.finditer(r"ConsumeBytes\s*<\s*[^>]+\s*>\s*\(\s*(\d+)\s*\)", prefix):
        try:
            total += int(m.group(1))
        except Exception:
            pass

    # Heuristic safety margin
    total += 32
    if total < 0:
        total = 0
    if total > 4096:
        total = 4096
    return total


def _detect_direct_data_offset(content: str) -> Optional[int]:
    # Look for "data + N" or "&data[N]" in lines that contain turbojpeg usage
    off = None
    for line in content.splitlines():
        if "tj" not in line and "TurboJPEG" not in line and "turbojpeg" not in line:
            continue
        if "data" not in line and "Data" not in line:
            continue
        for m in re.finditer(r"\bdata\s*\+\s*(\d+)\b", line, flags=re.IGNORECASE):
            try:
                n = int(m.group(1))
                if off is None or n < off:
                    off = n
            except Exception:
                pass
        for m in re.finditer(r"\&\s*data\s*\[\s*(\d+)\s*\]", line, flags=re.IGNORECASE):
            try:
                n = int(m.group(1))
                if off is None or n < off:
                    off = n
            except Exception:
                pass
    return off


def _expects_jpeg_input(content: Optional[str]) -> bool:
    if not content:
        return True
    kws = [
        "tj3Transform", "tjTransform",
        "tj3Decompress", "tjDecompress",
        "DecompressHeader", "tjDecompressHeader",
        "jpeg_read_header", "jpeg_read_scanlines",
    ]
    for kw in kws:
        if kw in content:
            return True
    return False


class Solution:
    def solve(self, src_path: str) -> bytes:
        name, content = _scan_tar_for_fuzzer_hint(src_path)

        if content is None:
            return _jpeg_constant_gray_baseline_444(256, 256)

        if not _expects_jpeg_input(content):
            # Likely raw/structured input fuzzer: provide a reasonably-sized buffer where early integral
            # consumes tend to become small/min values.
            # Start with 0x01 to avoid all-zeros special casing, then zeros.
            return b"\x01" + (b"\x00" * 16383)

        jpeg = _jpeg_constant_gray_baseline_444(256, 256)

        # If the fuzzer seems to use an offset into `data`, honor it.
        off = _detect_direct_data_offset(content)
        if off is not None and off > 0:
            prefix = bytearray(b"\x00" * off)
            prefix[0] = 1
            return bytes(prefix) + jpeg

        # If it uses FuzzedDataProvider and consumes a prefix before taking remaining bytes as JPEG,
        # add an estimated prefix.
        if "FuzzedDataProvider" in content and "ConsumeRemainingBytes" in content:
            prelen = _estimate_fdp_prefix_len(content)
            if prelen > 0:
                prefix = bytearray(b"\x00" * prelen)
                prefix[0] = 1
                return bytes(prefix) + jpeg

        return jpeg