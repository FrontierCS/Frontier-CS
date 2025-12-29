import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        class BitWriter:
            def __init__(self):
                self.buf = bytearray()
                self.cur = 0
                self.bits = 0
            def write_bits(self, value: int, nbits: int):
                v = value
                for _ in range(nbits):
                    bit = v & 1
                    v >>= 1
                    self.cur |= (bit << self.bits)
                    self.bits += 1
                    if self.bits == 8:
                        self.buf.append(self.cur)
                        self.cur = 0
                        self.bits = 0
            def finish(self) -> bytes:
                if self.bits:
                    self.buf.append(self.cur)
                    self.cur = 0
                    self.bits = 0
                return bytes(self.buf)

        w = BitWriter()
        # BFINAL=1, BTYPE=2 (dynamic)
        w.write_bits(1, 1)
        w.write_bits(2, 2)
        # HLIT=0 (257 lit/len codes), HDIST=0 (1 dist), HCLEN=15 (19 code length codes)
        w.write_bits(0, 5)
        w.write_bits(0, 5)
        w.write_bits(15, 4)

        # Code length code order:
        cl_order = [16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15]
        # We set lengths for symbols 18 and 1 to 1, rest 0
        cl_lengths = []
        for sym in cl_order:
            if sym in (18, 1):
                cl_lengths.append(1)
            else:
                cl_lengths.append(0)
        for l in cl_lengths:
            w.write_bits(l, 3)

        # With CL tree: code(1)=0, code(18)=1 (canonical with two symbols of length 1)
        # Encode literal/length code lengths: 256 zeros then one '1' for symbol 256
        # 256 zeros as 138 + 118 zeros using symbol 18 with extra bits
        # First run: 138 zeros -> write symbol 18 (code '1') + 7 extra bits (127)
        w.write_bits(1, 1)       # symbol 18
        w.write_bits(127, 7)     # 138 zeros (11 + 127)
        # Second run: 118 zeros -> symbol 18 + extra 107
        w.write_bits(1, 1)       # symbol 18
        w.write_bits(107, 7)     # 118 zeros (11 + 107)
        # Now one '1' for symbol 256 length -> symbol 1 has code '0'
        w.write_bits(0, 1)       # symbol 1

        # Distance code lengths: 1 code, set length to 1 -> symbol 1
        w.write_bits(0, 1)       # symbol 1

        # Now the actual block data: single end-of-block symbol 256 using lit/len tree
        # Our lit/len tree has only symbol 256 with length 1, which gets code '0'
        w.write_bits(0, 1)       # EOB

        deflate_data = w.finish()

        # GZIP header
        gz_header = bytes([
            0x1f, 0x8b,       # ID1, ID2
            0x08,             # CM = deflate
            0x00,             # FLG = 0
            0x00, 0x00, 0x00, 0x00,  # MTIME
            0x00,             # XFL
            0xff              # OS (unknown)
        ])

        # Uncompressed data is empty, so CRC32 and ISIZE are 0
        crc = zlib.crc32(b'') & 0xffffffff
        isize = 0
        gz_trailer = struct.pack('<II', crc, isize)

        return gz_header + deflate_data + gz_trailer