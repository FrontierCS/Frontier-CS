import io
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        bio = io.BytesIO()
        long_name = "A" * 300 + ".dae"
        with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_STORED) as zf:
            zf.writestr(long_name, b"content")
        return bio.getvalue()
