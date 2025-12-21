import struct
import zlib


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Find a small original payload that produces a Huffman-coded DEFLATE stream
        best_gzip = None
        best_len = None

        for size in range(1, 64):
            orig = b"A" * size
            comp = self._deflate_raw(orig)
            if not comp:
                continue
            if not self._has_huffman_block(comp):
                continue
            gz = self._make_gzip(comp, orig)
            l = len(gz)
            if best_gzip is None or l < best_len:
                best_gzip = gz
                best_len = l

        if best_gzip is None:
            # Fallback: just compress a larger payload; zlib will definitely use Huffman coding
            orig = b"A" * 1024
            comp = self._deflate_raw(orig)
            best_gzip = self._make_gzip(comp, orig)

        return best_gzip

    def _deflate_raw(self, data: bytes) -> bytes:
        compobj = zlib.compressobj(level=9, method=zlib.DEFLATED, wbits=-15)
        return compobj.compress(data) + compobj.flush()

    def _make_gzip(self, deflate_data: bytes, orig: bytes) -> bytes:
        # GZIP header: ID1 ID2 CM FLG MTIME[4] XFL OS
        header = b"\x1f\x8b"  # ID1, ID2
        header += b"\x08"     # CM = DEFLATE
        header += b"\x00"     # FLG = 0 (no extra fields)
        header += b"\x00\x00\x00\x00"  # MTIME = 0
        header += b"\x00"     # XFL = 0
        header += b"\xff"     # OS = 255 (unknown)

        crc = zlib.crc32(orig) & 0xFFFFFFFF
        isize = len(orig) & 0xFFFFFFFF
        footer = struct.pack("<II", crc, isize)

        return header + deflate_data + footer

    def _has_huffman_block(self, data: bytes) -> bool:
        """Return True if the raw DEFLATE stream has at least one Huffman-coded block."""
        bitpos = 0
        nbits = len(data) * 8

        while True:
            if bitpos + 3 > nbits:
                return False

            byte_index = bitpos >> 3
            bit_offset = bitpos & 7

            if byte_index + 1 < len(data):
                x = data[byte_index] | (data[byte_index + 1] << 8)
            else:
                x = data[byte_index]

            x >>= bit_offset
            bfinal = x & 1
            btype = (x >> 1) & 0b11

            if btype in (1, 2):
                return True
            if btype == 3:
                # Reserved (invalid) - shouldn't happen for zlib output
                return False

            # btype == 0: uncompressed block
            # Skip the remaining bits of header to the next byte boundary
            bitpos += 3
            bitpos = (bitpos + 7) & ~7  # align to next byte

            if bitpos + 32 > nbits:
                return False
            byte_index = bitpos >> 3
            if byte_index + 3 >= len(data):
                return False

            # LEN and NLEN (we only need LEN)
            length = data[byte_index] | (data[byte_index + 1] << 8)
            bitpos += 32  # skip LEN and NLEN fields

            # Skip LEN bytes of uncompressed data
            bitpos += length * 8
            if bitpos > nbits:
                return False

            if bfinal:
                break

        return False
