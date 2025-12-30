import zipfile
from io import BytesIO

class Solution:
    def solve(self, src_path: str) -> bytes:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_STORED) as zf:
            long_name = b'A' * 300
            zf.writestr(long_name, b'')
        return buffer.getvalue()