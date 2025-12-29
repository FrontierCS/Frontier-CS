import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        data = b'\x00' * 16
        file_size = 54 + len(data)
        file_header = struct.pack('<2sIHHI', b'BM', file_size, 0, 0, 54)
        dib_header = struct.pack('<IiiHHIIIiiII',
            40,
            1,  # biWidth
            0,  # biHeight
            1,  # biPlanes
            24, # biBitCount
            0,  # biCompression
            len(data), # biSizeImage
            0,  # biXPelsPerMeter
            0,  # biYPelsPerMeter
            0,  # biClrUsed
            0   # biClrImportant
        )
        return file_header + dib_header + data