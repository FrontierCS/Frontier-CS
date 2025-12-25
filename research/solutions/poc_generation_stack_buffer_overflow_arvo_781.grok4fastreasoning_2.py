import tarfile
import os
import tempfile
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path) as tar:
                tar.extractall(tmpdir)
            c_path = None
            for root, _, files in os.walk(tmpdir):
                for f in files:
                    if f.endswith('.c'):
                        c_path = os.path.join(root, f)
                        break
                if c_path:
                    break
            if not c_path:
                raise ValueError("No C file found")
            with open(c_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Regex to find subject definition like: [const char *] subject = "string";
            pat = r'(?:(?:const\s+(?:unsigned\s+)?char\s*\*?\s+)?subject\s*=\s*)"([^"]*)"'
            match = re.search(pat, content)
            if not match:
                raise ValueError("Could not find subject string")
            subject_str = match.group(1)
            return subject_str.encode('ascii')
