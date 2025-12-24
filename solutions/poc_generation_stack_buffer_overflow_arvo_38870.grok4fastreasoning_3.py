import zipfile
import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode='w', compression=zipfile.ZIP_STORED) as zf:
            filename = 'A' * 257
            zf.writestr(filename, b'')
        buf.seek(0)
        return buf.read()
