class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'\x80\x02\x03\x48'
        value = b'A' * 840
        return header + value