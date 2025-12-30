import io
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        long_name = "a" * 300 + ".dae"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_STORED, allowZip64=False) as zf:
            zf.writestr(long_name, b"x")
        return buf.getvalue()