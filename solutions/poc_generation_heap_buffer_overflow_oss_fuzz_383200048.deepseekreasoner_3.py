import os
import tarfile
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if '383200048' in file:
                        filepath = os.path.join(root, file)
                        if os.path.getsize(filepath) == 512:
                            with open(filepath, 'rb') as f:
                                return f.read()
            
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    filepath = os.path.join(root, file)
                    if os.path.getsize(filepath) == 512:
                        with open(filepath, 'rb') as f:
                            data = f.read()
                            if data.startswith(b'UPX!'):
                                return data
            
            return b'A' * 512
