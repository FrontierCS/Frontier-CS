import os
import re
import tarfile
from typing import Dict, Iterable, Optional, Tuple


def _u16be(n: int) -> bytes:
    return bytes([(n >> 8) & 0xFF, n & 0xFF])


def _stuff_ff(data: bytes) -> bytes:
    if b"\xFF" not in data:
        return data
    out = bytearray()
    for b in data:
        out.append(b)
        if b == 0xFF:
            out.append(0x00)
    return bytes(out)


def _make_minimal_jpeg_ycbcr_420(w: int = 256, h: int = 256) -> bytes:
    if w <= 0 or h <= 0 or w > 65535 or h > 65535:
        raise ValueError("Invalid dimensions")
    # Use 4:2:0 sampling (MCU is 16x16): Y=2x2, Cb/Cr=1x1.
    # Minimal Huffman tables:
    # - DC table 0: 2 codes of length 1: symbols [0,1] (complete tree)
    # - AC table 0: 2 codes of length 1: symbols [0x00(EOB), 0x01] (complete tree)
    # We then encode only symbol 0 for DC and symbol 0x00 for AC, so bits are all 0.

    # Compute number of MCUs and blocks needed
    mcus_x = (w + 15) // 16
    mcus_y = (h + 15) // 16
    mcus = mcus_x * mcus_y
    blocks_per_mcu = 6  # 4 Y + 1 Cb + 1 Cr
    total_blocks = mcus * blocks_per_mcu
    total_bits = total_blocks * 2  # DC(0) + AC(EOB), each 1 bit

    full_bytes = total_bits // 8
    rem_bits = total_bits % 8
    entropy = bytearray(b"\x00" * full_bytes)
    if rem_bits:
        # remaining bits are zeros, pad with ones to byte boundary
        pad_ones = 8 - rem_bits
        last_byte = (1 << pad_ones) - 1
        entropy.append(last_byte & 0xFF)

    entropy_bytes = _stuff_ff(bytes(entropy))

    # Segments
    soi = b"\xFF\xD8"

    # DQT: one table, all 1s
    qt = b"\x01" * 64
    dqt_payload = b"\x00" + qt  # Pq/Tq
    dqt = b"\xFF\xDB" + _u16be(2 + len(dqt_payload)) + dqt_payload

    # SOF0: baseline, 3 components, 4:2:0 sampling
    sof_payload = bytearray()
    sof_payload.append(0x08)  # precision
    sof_payload += _u16be(h)
    sof_payload += _u16be(w)
    sof_payload.append(3)  # components
    # Y
    sof_payload += bytes([1, 0x22, 0])  # id, sampling, qtable
    # Cb
    sof_payload += bytes([2, 0x11, 0])
    # Cr
    sof_payload += bytes([3, 0x11, 0])
    sof0 = b"\xFF\xC0" + _u16be(2 + len(sof_payload)) + bytes(sof_payload)

    # DHT: DC0 and AC0 minimal complete trees
    bits_len1_2 = bytes([2] + [0] * 15)
    dht_payload = bytearray()
    # DC table 0 (Tc=0, Th=0)
    dht_payload.append(0x00)
    dht_payload += bits_len1_2
    dht_payload += bytes([0, 1])
    # AC table 0 (Tc=1, Th=0)
    dht_payload.append(0x10)
    dht_payload += bits_len1_2
    dht_payload += bytes([0x00, 0x01])
    dht = b"\xFF\xC4" + _u16be(2 + len(dht_payload)) + bytes(dht_payload)

    # SOS: 3 components, table 0 for both DC/AC
    sos_payload = bytearray()
    sos_payload.append(3)  # Ns
    sos_payload += bytes([1, 0x00])
    sos_payload += bytes([2, 0x00])
    sos_payload += bytes([3, 0x00])
    sos_payload += bytes([0, 63, 0])  # Ss, Se, Ah/Al
    sos = b"\xFF\xDA" + _u16be(2 + len(sos_payload)) + bytes(sos_payload)

    eoi = b"\xFF\xD9"
    return soi + dqt + sof0 + dht + sos + entropy_bytes + eoi


def _extract_llvm_fuzzer_body(text: str) -> Optional[str]:
    idx = text.find("LLVMFuzzerTestOneInput")
    if idx < 0:
        return None
    brace = text.find("{", idx)
    if brace < 0:
        return None

    i = brace
    n = len(text)
    depth = 0
    in_sl_comment = False
    in_ml_comment = False
    in_dq = False
    in_sq = False
    esc = False

    while i < n:
        c = text[i]

        if in_sl_comment:
            if c == "\n":
                in_sl_comment = False
            i += 1
            continue

        if in_ml_comment:
            if c == "*" and (i + 1) < n and text[i + 1] == "/":
                in_ml_comment = False
                i += 2
            else:
                i += 1
            continue

        if in_dq:
            if esc:
                esc = False
                i += 1
                continue
            if c == "\\":
                esc = True
                i += 1
                continue
            if c == '"':
                in_dq = False
            i += 1
            continue

        if in_sq:
            if esc:
                esc = False
                i += 1
                continue
            if c == "\\":
                esc = True
                i += 1
                continue
            if c == "'":
                in_sq = False
            i += 1
            continue

        if c == "/" and (i + 1) < n:
            nxt = text[i + 1]
            if nxt == "/":
                in_sl_comment = True
                i += 2
                continue
            if nxt == "*":
                in_ml_comment = True
                i += 2
                continue

        if c == '"':
            in_dq = True
            i += 1
            continue
        if c == "'":
            in_sq = True
            i += 1
            continue

        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[brace : i + 1]
        i += 1
    return None


def _sizeof_cxx_type(t: str) -> int:
    t = t.strip()
    t = re.sub(r"\b(const|volatile|signed)\b", " ", t)
    t = t.replace("&", " ").replace("*", " ")
    t = " ".join(t.split())
    if not t:
        return 4
    if "uint8_t" in t or "int8_t" in t or t in ("char", "unsigned char", "signed char", "std::byte", "byte", "bool"):
        return 1
    if "uint16_t" in t or "int16_t" in t or t in ("short", "unsigned short"):
        return 2
    if "uint32_t" in t or "int32_t" in t or t in ("int", "unsigned", "unsigned int", "float"):
        return 4
    if "uint64_t" in t or "int64_t" in t or "size_t" in t or "ssize_t" in t or "ptrdiff_t" in t or t in (
        "long",
        "unsigned long",
        "long long",
        "unsigned long long",
        "double",
    ):
        return 8
    return 4


def _estimate_prefix_from_fdp(pre: str) -> int:
    total = 0

    # ConsumeBool()
    total += len(re.findall(r"\bConsumeBool\s*\(\s*\)", pre))

    # ConsumeIntegral*/ConsumeEnum/ConsumeFloatingPoint
    for m in re.finditer(
        r"\bConsume(?:IntegralInRange|Integral|Enum|FloatingPoint)\s*<\s*([^>]+?)\s*>\s*\(",
        pre,
    ):
        total += _sizeof_cxx_type(m.group(1))

    # Fixed-size ConsumeBytes/ConsumeBytesAsString with literal length
    for m in re.finditer(r"\bConsumeBytes(?:AsString)?(?:\s*<[^>]*>)?\s*\(\s*(\d+)\s*\)", pre):
        try:
            total += int(m.group(1))
        except Exception:
            pass

    return total


def _score_fuzzer_source(text: str, path: str) -> int:
    low = (path + "\n" + text).lower()
    s = 0
    if "llvmfuzzertestoneinput" in low:
        s += 10
    s += 10 * low.count("tj3")
    s += 6 * low.count("tj3transform")
    s += 6 * low.count("tjtransform")
    s += 5 * low.count("tj3compress")
    s += 4 * low.count("tjcompress")
    s += 5 * low.count("tj3decompress")
    s += 4 * low.count("tjdecompress")
    s += 6 * low.count("tj3alloc")
    if "fuzzedataprovider" in low:
        s += 5
    if "fuzz" in low:
        s += 3
    return s


def _iter_sources_from_dir(root: str) -> Iterable[Tuple[str, bytes]]:
    exts = {".c", ".cc", ".cpp", ".cxx", ".c++", ".h", ".hpp"}
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            _, ext = os.path.splitext(fn)
            if ext.lower() not in exts:
                continue
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
                if st.st_size <= 0 or st.st_size > 2_000_000:
                    continue
                with open(p, "rb") as f:
                    yield p, f.read()
            except Exception:
                continue


def _iter_sources_from_tar(tar_path: str) -> Iterable[Tuple[str, bytes]]:
    exts = {".c", ".cc", ".cpp", ".cxx", ".c++", ".h", ".hpp"}
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                _, ext = os.path.splitext(name)
                if ext.lower() not in exts:
                    continue
                if m.size <= 0 or m.size > 2_000_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                    yield name, data
                except Exception:
                    continue
    except Exception:
        return


def _infer_prefix_len(src_path: str) -> int:
    if os.path.isdir(src_path):
        it = _iter_sources_from_dir(src_path)
    else:
        it = _iter_sources_from_tar(src_path)

    best_score = -1
    best_path = None
    best_text = None

    for path, data in it:
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            continue
        if "LLVMFuzzerTestOneInput" not in text:
            continue
        sc = _score_fuzzer_source(text, path)
        if sc > best_score:
            best_score = sc
            best_path = path
            best_text = text

    if not best_text:
        return 0

    body = _extract_llvm_fuzzer_body(best_text)
    if not body:
        return 0

    # If it uses FuzzedDataProvider and takes remaining bytes as the payload, estimate fixed prefix consumption.
    if "FuzzedDataProvider" in body and "ConsumeRemainingBytes" in body:
        idx = body.find("ConsumeRemainingBytes")
        pre = body[:idx]
        plen = _estimate_prefix_from_fdp(pre)
        if 0 < plen <= 4096:
            return plen

    # Otherwise, look for constant offsets used directly in a decompression/transform call
    off_candidates = []
    for m in re.finditer(r"\btj(?:3)?(?:Decompress|Transform)\w*\s*\(([^;]{0,400})\)", body):
        args = m.group(1)
        for o in re.finditer(r"\bdata\s*\+\s*(\d+)\b", args):
            try:
                off_candidates.append(int(o.group(1)))
            except Exception:
                pass

    if off_candidates:
        mn = min(off_candidates)
        if 0 < mn <= 4096:
            return mn

    # Heuristic: pick a small constant from "data += N" if present
    add_candidates = []
    for o in re.finditer(r"\bdata\s*\+=\s*(\d+)\s*;", body):
        try:
            add_candidates.append(int(o.group(1)))
        except Exception:
            pass
    if add_candidates:
        mn = min(add_candidates)
        if 0 < mn <= 4096:
            return mn

    return 0


class Solution:
    def solve(self, src_path: str) -> bytes:
        prefix_len = 0
        try:
            prefix_len = _infer_prefix_len(src_path)
        except Exception:
            prefix_len = 0

        jpeg = _make_minimal_jpeg_ycbcr_420(256, 256)

        if prefix_len <= 0:
            return jpeg

        prefix = bytearray()
        for i in range(prefix_len):
            prefix.append(0x01 if (i & 1) == 0 else 0x00)
        return bytes(prefix) + jpeg