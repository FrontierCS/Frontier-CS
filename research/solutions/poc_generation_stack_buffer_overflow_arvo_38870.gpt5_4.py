import io
import zipfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        buf = io.BytesIO()
        long_name = "A" * 300 + ".txt"
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
            zf.writestr(long_name, b"X")
        return buf.getvalue()