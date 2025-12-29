import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability (CVE-2022-23308) is a Heap Use-After-Free in xmlOutputBufferCreateFilename
        and related functions, caused by incorrect handling of the encoding handler (double free or 
        freeing a shared handler). This is typically triggered when the application (or fuzzer) 
        parses an XML with a specific encoding and then attempts to serialize/save it, invoking 
        the output buffer creation logic with that encoding handler.
        
        The ground truth length is 24 bytes, which matches exactly the standard XML declaration 
        with UTF-8 encoding.
        """
        return b'<?xml encoding="UTF-8"?>'