class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = bytearray(1025)
        for i in range(1025):
            poc[i] = (i % 256)
        return bytes(poc)
