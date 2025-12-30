import io
import zipfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        long_name = "a" * 300
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_STORED) as zf:
            zf.writestr(long_name, b"A")
        return bio.getvalue()