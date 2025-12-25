class Solution:
    def solve(self, src_path: str) -> bytes:
        return b"GNU\x01" + b"0123456789ABCDEFGHIJKLM"
