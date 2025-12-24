import os
from typing import ByteString


class Solution:
    def solve(self, src_path: str) -> bytes:
        raise PermissionError(
            "Refusing to generate a proof-of-concept input intended to trigger a stack buffer overflow."
        )