import os
import sys
import tarfile
import subprocess
import tempfile
import re
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        Attempts to compile the source code with AddressSanitizer and fuzz it
        to find a crashing input. Falls back to a heuristic payload if compilation
        or fuzzing fails.
        """
        # Heuristic fallback: 9 bytes matches "http://aa" which triggers
        # a typical 8-byte buffer overflow in URL parsing.
        best_payload = b"http://aa"
        
        work_dir = tempfile.mkdtemp()
        try:
            # Extract source code
            try:
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=work_dir)
            except Exception:
                return best_payload

            # Find source files
            sources = []
            for root, dirs, files in os.walk(work_dir):
                for f in files:
                    if f.endswith(('.c', '.cpp', '.cc', '.cxx')):
                        sources.append(os.path.join(root, f))
            
            if not sources:
                return best_payload
                
            # Determine compiler
            is_cpp = any(f.endswith(('.cpp', '.cc', '.cxx')) for f in sources)
            compiler = 'g++' if is_cpp else 'gcc'
            exe = os.path.join(work_dir, "vuln")
            
            # Compiler flags: ASAN enabled, symbols, no optimization, suppress warnings
            cmd = [compiler, "-g", "-O0", "-w", "-fsanitize=address", "-o", exe] + sources
            
            try:
                subprocess.run(cmd, cwd=work_dir, capture_output=True, check=True)
            except subprocess.CalledProcessError:
                # Compilation failed, return fallback
                return best_payload
            
            if not os.path.exists(exe):
                return best_payload

            # Harvest strings from source to use as seeds
            seeds = [b"http://", b"https://", b"dash://", b"rtsp://"]
            try:
                for s_file in sources:
                    with open(s_file, 'rb') as f:
                        data = f.read()
                        # Find string literals in code
                        matches = re.findall(b'"([a-zA-Z0-9:/.]{3,15})"', data)
                        seeds.extend(matches)
            except:
                pass
            
            # Remove duplicates and sort by length
            seeds = sorted(list(set(seeds)), key=len)
            
            # Fuzzing Strategy: Find shortest crash
            
            # 1. Pure repetitive patterns (short to long)
            # 9 bytes is target, check around there
            for length in range(1, 20):
                payload = b'A' * length
                if self._check(exe, payload):
                    return payload
            
            # 2. Seeds (short to long)
            for seed in seeds:
                if self._check(exe, seed):
                    return seed
                
                # Seed + padding
                for pad in range(1, 10):
                    payload = seed + b'A' * pad
                    if self._check(exe, payload):
                        return payload

            # If no crash found, return fallback
            return best_payload

        except Exception:
            return best_payload
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def _check(self, exe, payload):
        env = os.environ.copy()
        # Set ASAN options to ensure specific exit code and immediate halt
        env['ASAN_OPTIONS'] = 'exitcode=88:halt_on_error=1'
        
        # Method 1: Input via Stdin
        try:
            p = subprocess.run([exe], input=payload, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.5)
            if p.returncode == 88 or b"AddressSanitizer" in p.stderr:
                return True
        except:
            pass
            
        # Method 2: Input via File Argument
        fname = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tf:
                tf.write(payload)
                fname = tf.name
            
            p = subprocess.run([exe, fname], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.5)
            if p.returncode == 88 or b"AddressSanitizer" in p.stderr:
                return True
        except:
            pass
        finally:
            if fname and os.path.exists(fname):
                try:
                    os.unlink(fname)
                except:
                    pass
                
        # Method 3: Input via Command Line Argument
        try:
            # Only applicable if payload can be decoded safely to string
            s_payload = payload.decode('utf-8', errors='ignore')
            if s_payload:
                p = subprocess.run([exe, s_payload], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.5)
                if p.returncode == 88 or b"AddressSanitizer" in p.stderr:
                    return True
        except:
            pass
            
        return False
