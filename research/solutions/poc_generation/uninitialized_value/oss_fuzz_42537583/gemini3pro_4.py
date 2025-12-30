import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability is an uninitialized value usage in the media100_to_mjpegb 
        bitstream filter due to uncleared output buffer padding.
        The filter requires a minimum packet size of 40 bytes.
        Providing a buffer of zeros larger than 40 bytes (e.g., 128 bytes) 
        bypasses the initial size check, is interpreted as a valid progressive frame, 
        and triggers the creation of an output packet where the padding bytes are 
        left uninitialized, causing an MSan error in the vulnerable version.
        """
        return bytes(128)