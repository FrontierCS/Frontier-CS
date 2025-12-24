import io
import zipfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED) as z:
            long_name = 'A' * 300
            z.writestr(long_name, b'')
        return buf.getvalue()
