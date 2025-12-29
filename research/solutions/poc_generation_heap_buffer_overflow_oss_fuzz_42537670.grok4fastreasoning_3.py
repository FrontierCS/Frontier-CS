class Solution:
    def solve(self, src_path: str) -> bytes:
        return b'\x99' + b'\x92\x7f' + b'\x99' + b'\x92\x7f' * 9373 + b'\x00' * (37535 - 8 - 9373*2)