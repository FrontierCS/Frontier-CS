import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        def build_canonical_codes(code_lengths):
            max_bits = max(code_lengths) if code_lengths else 0
            if max_bits == 0:
                return [0] * len(code_lengths), list(code_lengths)
            bl_count = [0] * (max_bits + 1)
            for length in code_lengths:
                if length > 0:
                    bl_count[length] += 1
            code = 0
            next_code = [0] * (max_bits + 1)
            for bits in range(1, max_bits + 1):
                code = (code + bl_count[bits - 1]) << 1
                next_code[bits] = code
            codes = [0] * len(code_lengths)
            for n, length in enumerate(code_lengths):
                if length != 0:
                    codes[n] = next_code[length]
                    next_code[length] += 1
            return codes, list(code_lengths)

        def put_bits(bits_list, value, bit_count):
            for i in range(bit_count):
                bits_list.append((value >> i) & 1)

        # Build a single dynamic Huffman block that encodes an empty stream.
        bits = []

        # BFINAL=1 (last block), BTYPE=2 (dynamic Huffman)
        put_bits(bits, 1, 1)  # BFINAL
        put_bits(bits, 2, 2)  # BTYPE=2

        # HLIT, HDIST, HCLEN
        HLIT = 29   # 286 literal/length codes (max)
        HDIST = 0   # 1 distance code
        HCLEN = 15  # 19 code length codes

        put_bits(bits, HLIT, 5)
        put_bits(bits, HDIST, 5)
        put_bits(bits, HCLEN, 4)

        # Code length code lengths (for 19 symbols, values 0..18) in specified order
        # We set lengths: symbol 0 -> 1, symbol 15 -> 1, others -> 0
        cl_lengths = [0] * 19
        cl_lengths[0] = 1   # symbol 0
        cl_lengths[15] = 1  # symbol 15

        order = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]
        for sym in order:
            length = cl_lengths[sym]
            put_bits(bits, length, 3)  # 3-bit lengths for code length alphabet

        # Build canonical codes for code length alphabet
        cl_codes, cl_lengths_out = build_canonical_codes(cl_lengths)

        # Now encode literal/length and distance code lengths
        num_litlen = 257 + HLIT   # 286
        num_dist = 1 + HDIST      # 1
        total_codes = num_litlen + num_dist  # 287

        sym_for_15 = 15
        cl_code_val = cl_codes[sym_for_15]
        cl_code_len = cl_lengths_out[sym_for_15]

        # Set all code lengths (litlen + dist) to 15 by emitting symbol 15 repeatedly
        for _ in range(total_codes):
            put_bits(bits, cl_code_val, cl_code_len)

        # Build canonical codes for litlen alphabet to encode EOB (256)
        litlen_lengths = [15] * num_litlen
        litlen_codes, litlen_lengths_out = build_canonical_codes(litlen_lengths)
        eob_symbol = 256
        eob_code = litlen_codes[eob_symbol]
        eob_len = litlen_lengths_out[eob_symbol]

        # Emit EOB symbol as the only data in the block
        put_bits(bits, eob_code, eob_len)

        # Convert bit stream to bytes (LSB-first per byte)
        def bits_to_bytes(bits_seq):
            out = bytearray()
            curr = 0
            bit_pos = 0
            for b in bits_seq:
                curr |= (b & 1) << bit_pos
                bit_pos += 1
                if bit_pos == 8:
                    out.append(curr)
                    curr = 0
                    bit_pos = 0
            if bit_pos > 0:
                out.append(curr)
            return bytes(out)

        deflate_data = bits_to_bytes(bits)

        # Build minimal gzip wrapper around the deflate stream
        # Uncompressed data is empty, so CRC32=0 and ISIZE=0
        header = bytearray()
        header.extend(b"\x1f\x8b")          # ID1, ID2
        header.append(8)                   # CM = deflate
        header.append(0)                   # FLG = 0 (no extra fields)
        header.extend(struct.pack("<I", 0))  # MTIME = 0
        header.append(0)                   # XFL
        header.append(255)                 # OS = unknown (255)

        crc32 = 0
        isize = 0
        trailer = struct.pack("<II", crc32, isize)

        return bytes(header) + deflate_data + trailer