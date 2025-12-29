from io import BytesIO
import zipfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        bio = BytesIO()
        with zipfile.ZipFile(bio, 'w') as zf:
            zf.writestr('A' * 300, b'')
        return bio.getvalue()