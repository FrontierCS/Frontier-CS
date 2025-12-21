import io
import zipfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zf:
            zf.writestr('A' * 260, b'')
        return buffer.getvalue()
