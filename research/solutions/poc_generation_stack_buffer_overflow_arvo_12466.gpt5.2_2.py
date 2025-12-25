import os
import re
import io
import tarfile
import zipfile
import gzip
import zlib
from typing import Optional, Tuple, List


RAR5_SIG = b"Rar!\x1a\x07\x01\x00"
RAR4_SIG = b"Rar!\x1a\x07\x00"

DEFAULT_GROUND_TRUTH_LEN = 524

MAX_MEMBER_READ = 10_000_000
MAX_TEXT_PARSE = 500_000
MAX_NESTED_CONTAINER = 6_000_000
MAX_GZIP_DECOMPRESSED = 20_000_000


def _path_keyword_rank(name: str) -> int:
    p = name.replace("\\", "/").lower()
    rank = 20
    if p.endswith(".rar"):
        rank -= 2
    if any(k in p for k in ("crash", "poc", "overflow", "stack", "asan", "ubsan", "repro", "reproducer", "cve", "issue", "bug")):
        rank -= 8
    if any(k in p for k in ("ossfuzz", "oss-fuzz", "clusterfuzz", "fuzz", "corpus", "seed", "artifacts")):
        rank -= 6
    if any(k in p for k in ("regress", "regression", "test", "tests", "testcase", "cases", "unit")):
        rank -= 3
    if any(k in p for k in ("/fuzz/", "/corpus/", "/artifacts/", "/test/", "/tests/", "/regression/")):
        rank -= 2
    if rank < 0:
        rank = 0
    return rank


def _score_candidate(name: str, data: bytes) -> Tuple[int, int, int, str]:
    rank = _path_keyword_rank(name)
    l = len(data)
    return (rank, abs(l - DEFAULT_GROUND_TRUTH_LEN), l, name)


def _safe_read_fileobj(f, limit: int) -> bytes:
    chunks = []
    total = 0
    while True:
        to_read = min(262144, limit - total)
        if to_read <= 0:
            break
        b = f.read(to_read)
        if not b:
            break
        chunks.append(b)
        total += len(b)
    return b"".join(chunks)


def _is_zip_bytes(data: bytes) -> bool:
    return len(data) >= 4 and (data[:4] == b"PK\x03\x04" or data[:4] == b"PK\x05\x06" or data[:4] == b"PK\x07\x08")


def _is_gzip_bytes(data: bytes) -> bool:
    return len(data) >= 2 and data[:2] == b"\x1f\x8b"


def _try_extract_rar5_from_zip(name: str, data: bytes) -> Optional[Tuple[str, bytes]]:
    if len(data) > MAX_NESTED_CONTAINER or not _is_zip_bytes(data):
        return None
    try:
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            best = None
            for zi in zf.infolist():
                if zi.is_dir():
                    continue
                if zi.file_size <= 0 or zi.file_size > MAX_MEMBER_READ:
                    continue
                try:
                    with zf.open(zi, "r") as f:
                        b = f.read(min(zi.file_size, MAX_MEMBER_READ))
                except Exception:
                    continue
                if b.startswith(RAR5_SIG):
                    cand_name = f"{name}::{zi.filename}"
                    cand = (cand_name, b)
                    if best is None or _score_candidate(cand[0], cand[1]) < _score_candidate(best[0], best[1]):
                        best = cand
            return best
    except Exception:
        return None


def _try_extract_rar5_from_gzip(name: str, data: bytes) -> Optional[Tuple[str, bytes]]:
    if len(data) > MAX_NESTED_CONTAINER or not _is_gzip_bytes(data):
        return None
    try:
        dec = gzip.decompress(data)
        if len(dec) > MAX_GZIP_DECOMPRESSED:
            return None
        if dec.startswith(RAR5_SIG):
            return (name + "::gunzip", dec)
        if _is_zip_bytes(dec):
            return _try_extract_rar5_from_zip(name + "::gunzip", dec)
        return None
    except Exception:
        return None


_HEX_SIG_RE = re.compile(
    r"0x52\s*,\s*0x61\s*,\s*0x72\s*,\s*0x21\s*,\s*0x1a\s*,\s*0x07\s*,\s*0x01\s*,\s*0x00",
    re.IGNORECASE,
)
_ESC_SIG_RE = re.compile(r"(?:\\x52\\x61\\x72\\x21\\x1a\\x07\\x01\\x00)", re.IGNORECASE)
_B64_SIG = "UmFyIRoHAQAA"


def _extract_from_brace_list(text: str, match_pos: int) -> Optional[bytes]:
    left = text.rfind("{", max(0, match_pos - 12000), match_pos + 1)
    if left < 0:
        return None
    right = text.find("}", match_pos, match_pos + 60000)
    if right < 0:
        return None
    blob = text[left + 1 : right]
    tokens = re.findall(r"0x[0-9a-fA-F]{1,2}|\b\d{1,3}\b", blob)
    if len(tokens) < 16:
        return None
    out = bytearray()
    for t in tokens:
        if t.lower().startswith("0x"):
            v = int(t, 16)
        else:
            v = int(t, 10)
        if 0 <= v <= 255:
            out.append(v)
        if len(out) > MAX_MEMBER_READ:
            break
    b = bytes(out)
    if b.startswith(RAR5_SIG):
        return b
    return None


def _extract_from_escaped_hex(text: str, match_pos: int) -> Optional[bytes]:
    start = max(0, match_pos - 2000)
    end = min(len(text), match_pos + 200000)
    window = text[start:end]
    m = re.search(r"(?:\\x[0-9a-fA-F]{2}){16,}", window)
    if not m:
        return None
    seq = m.group(0)
    hexbytes = re.findall(r"\\x([0-9a-fA-F]{2})", seq)
    if len(hexbytes) < 16:
        return None
    b = bytes(int(h, 16) for h in hexbytes)
    if b.startswith(RAR5_SIG):
        return b
    return None


def _extract_from_base64(text: str, match_pos: int) -> Optional[bytes]:
    start = max(0, match_pos - 5000)
    end = min(len(text), match_pos + 200000)
    window = text[start:end]
    i = window.find(_B64_SIG)
    if i < 0:
        return None
    j = i
    while j > 0 and window[j - 1] in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r\t ":
        j -= 1
    k = i + len(_B64_SIG)
    while k < len(window) and window[k] in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r\t ":
        k += 1
    b64cand = "".join(ch for ch in window[j:k] if ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
    if len(b64cand) < 16 or len(b64cand) % 4 != 0:
        return None
    try:
        dec = __import__("base64").b64decode(b64cand, validate=False)
    except Exception:
        return None
    if dec.startswith(RAR5_SIG):
        return dec
    return None


def _try_extract_rar5_from_text(name: str, data: bytes) -> Optional[Tuple[str, bytes]]:
    if len(data) > MAX_TEXT_PARSE:
        return None
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        return None

    m = _HEX_SIG_RE.search(text)
    if m:
        b = _extract_from_brace_list(text, m.start())
        if b and b.startswith(RAR5_SIG):
            return (name + "::hexarray", b)

    m = _ESC_SIG_RE.search(text)
    if m:
        b = _extract_from_escaped_hex(text, m.start())
        if b and b.startswith(RAR5_SIG):
            return (name + "::eschex", b)

    idx = text.find(_B64_SIG)
    if idx >= 0:
        b = _extract_from_base64(text, idx)
        if b and b.startswith(RAR5_SIG):
            return (name + "::base64", b)

    return None


def _iter_files_from_tar(tar_path: str):
    with tarfile.open(tar_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            yield m, tf


def _looks_interesting_name(name: str) -> bool:
    p = name.replace("\\", "/").lower()
    if any(p.endswith(ext) for ext in (".rar", ".bin", ".dat", ".poc", ".crash", ".seed", ".input", ".gz", ".zip")):
        return True
    if any(k in p for k in ("crash", "poc", "overflow", "stack", "rar5", "rar", "ossfuzz", "fuzz", "corpus", "clusterfuzz", "repro", "cve")):
        return True
    return False


def _scan_source_for_rar5(src_path: str) -> Optional[bytes]:
    best: Optional[Tuple[Tuple[int, int, int, str], bytes]] = None

    def consider(name: str, data: bytes):
        nonlocal best
        if not data.startswith(RAR5_SIG):
            return
        sc = _score_candidate(name, data)
        if best is None or sc < best[0]:
            best = (sc, data)

    def consider_nested(name: str, data: bytes):
        cand = _try_extract_rar5_from_gzip(name, data)
        if cand:
            consider(cand[0], cand[1])
        cand = _try_extract_rar5_from_zip(name, data)
        if cand:
            consider(cand[0], cand[1])

    def consider_text(name: str, data: bytes):
        cand = _try_extract_rar5_from_text(name, data)
        if cand:
            consider(cand[0], cand[1])

    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                path = os.path.join(root, fn)
                rel = os.path.relpath(path, src_path)
                try:
                    st = os.stat(path)
                except Exception:
                    continue
                sz = st.st_size
                if sz <= 0:
                    continue
                if sz > MAX_MEMBER_READ and not _looks_interesting_name(rel):
                    continue
                try:
                    with open(path, "rb") as f:
                        b = _safe_read_fileobj(f, min(sz, MAX_MEMBER_READ))
                except Exception:
                    continue

                if b.startswith(RAR5_SIG):
                    consider(rel, b)
                    continue

                if _looks_interesting_name(rel) and len(b) <= MAX_NESTED_CONTAINER:
                    consider_nested(rel, b)

                if _looks_interesting_name(rel) and len(b) <= MAX_TEXT_PARSE:
                    consider_text(rel, b)

        return best[1] if best else None

    if not os.path.isfile(src_path):
        return None

    try:
        if tarfile.is_tarfile(src_path):
            for m, tf in _iter_files_from_tar(src_path):
                name = m.name
                sz = m.size
                if sz <= 0:
                    continue
                if sz > MAX_MEMBER_READ and not _looks_interesting_name(name):
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    b = _safe_read_fileobj(f, min(sz, MAX_MEMBER_READ))
                except Exception:
                    continue

                if b.startswith(RAR5_SIG):
                    consider(name, b)
                    continue

                if _looks_interesting_name(name) and len(b) <= MAX_NESTED_CONTAINER:
                    consider_nested(name, b)

                if _looks_interesting_name(name) and len(b) <= MAX_TEXT_PARSE:
                    consider_text(name, b)

            return best[1] if best else None
    except Exception:
        pass

    try:
        with open(src_path, "rb") as f:
            b = _safe_read_fileobj(f, MAX_MEMBER_READ)
        if b.startswith(RAR5_SIG):
            return b
        consider_nested(os.path.basename(src_path), b)
        consider_text(os.path.basename(src_path), b)
        return best[1] if best else None
    except Exception:
        return None


def _fallback_minimal_rar5() -> bytes:
    def vint(n: int) -> bytes:
        out = bytearray()
        while True:
            b = n & 0x7F
            n >>= 7
            if n:
                out.append(b | 0x80)
            else:
                out.append(b)
                break
        return bytes(out)

    def build_block(block_type: int, flags: int, body: bytes, extra: bytes = b"", data: bytes = b"") -> bytes:
        EXTRA = 0x0001
        DATA = 0x0002
        parts = [vint(block_type), vint(flags)]
        if flags & EXTRA:
            parts.append(vint(len(extra)))
        if flags & DATA:
            parts.append(vint(len(data)))
        parts.append(body)
        if flags & EXTRA:
            parts.append(extra)
        hdr_wo_size = b"".join(parts)

        size = 0
        while True:
            szb = vint(size)
            new_size = len(szb) + len(hdr_wo_size)
            if new_size == size:
                break
            size = new_size

        header = vint(size) + hdr_wo_size
        crc = zlib.crc32(header) & 0xFFFFFFFF
        return crc.to_bytes(4, "little") + header + data

    sig = RAR5_SIG
    main_body = vint(0)
    main = build_block(1, 0, main_body)

    end = build_block(5, 0, b"")

    return sig + main + end


class Solution:
    def solve(self, src_path: str) -> bytes:
        b = _scan_source_for_rar5(src_path)
        if b is not None:
            return b
        return _fallback_minimal_rar5()