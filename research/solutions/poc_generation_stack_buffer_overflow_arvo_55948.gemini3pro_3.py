import os
import tarfile
import subprocess
import tempfile
import shutil
import glob
import re
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp()
        
        try:
            # 1. Extract source code
            with tarfile.open(src_path) as tar:
                tar.extractall(path=work_dir)
            
            # Locate source root (handle tarball wrapping in a folder)
            src_root = work_dir
            entries = os.listdir(work_dir)
            if len(entries) == 1 and os.path.isdir(os.path.join(work_dir, entries[0])):
                src_root = os.path.join(work_dir, entries[0])
            
            # 2. Compile with AddressSanitizer
            env = os.environ.copy()
            flags = "-fsanitize=address -g -O0"
            env['CFLAGS'] = flags
            env['CXXFLAGS'] = flags
            env['LDFLAGS'] = flags
            env['CC'] = 'gcc'
            env['CXX'] = 'g++'
            
            # Look for Makefile
            makefile_dir = None
            for root, dirs, files in os.walk(src_root):
                if 'Makefile' in files:
                    makefile_dir = root
                    break
            
            built = False
            if makefile_dir:
                try:
                    subprocess.run(['make', 'clean'], cwd=makefile_dir, env=env, capture_output=True)
                    subprocess.run(['make'], cwd=makefile_dir, env=env, capture_output=True)
                    built = True
                except:
                    pass
            
            # 3. Locate Executable
            executable = None
            
            def is_candidate(path):
                return os.access(path, os.X_OK) and not path.endswith(('.sh', '.py', '.c', '.h', '.o', '.po'))
            
            candidates = []
            for root, dirs, files in os.walk(src_root):
                for f in files:
                    fp = os.path.join(root, f)
                    if is_candidate(fp):
                        # Filter out obviously wrong binaries like tests unless necessary
                        if 'test' in f.lower() or 'sample' in f.lower():
                            continue
                        candidates.append(fp)
            
            if candidates:
                # Prefer binary matching directory name or 'vuln'
                candidates.sort(key=lambda x: len(x)) # Simple heuristic
                executable = candidates[0]
                base_name = os.path.basename(src_root)
                for c in candidates:
                    if os.path.basename(c) == base_name:
                        executable = c
                        break
            
            # Fallback compilation if no executable found
            if not executable:
                c_files = glob.glob(os.path.join(src_root, "*.c"))
                if c_files:
                    executable = os.path.join(src_root, "vuln_app")
                    subprocess.run(['gcc', '-fsanitize=address', '-g'] + c_files + ['-o', executable], env=env, capture_output=True)
            
            if not executable or not os.path.exists(executable):
                return b""

            # 4. Find Sample Config / Template
            template = b""
            config_files = []
            for root, dirs, files in os.walk(src_root):
                for f in files:
                    if f.endswith(('.conf', '.cfg', '.ini', '.xml')):
                        config_files.append(os.path.join(root, f))
            
            if config_files:
                # Prefer 'example' or 'default'
                best_cfg = config_files[0]
                for c in config_files:
                    if 'example' in c or 'default' in c:
                        best_cfg = c
                        break
                with open(best_cfg, 'rb') as f:
                    template = f.read()
            else:
                # Minimal fallback based on problem description (hex config)
                template = b"value = 0x0\n"

            # 5. Fuzzing & Minimization
            
            def check_crash(payload_bytes):
                tfd, tpath = tempfile.mkstemp()
                os.write(tfd, payload_bytes)
                os.close(tfd)
                try:
                    # Method A: File argument
                    proc = subprocess.run([executable, tpath], capture_output=True, timeout=1)
                    if proc.returncode != 0 and b"AddressSanitizer" in proc.stderr:
                        return True
                    
                    # Method B: Stdin
                    with open(tpath, 'rb') as f:
                        proc = subprocess.run([executable], stdin=f, capture_output=True, timeout=1)
                        if proc.returncode != 0 and b"AddressSanitizer" in proc.stderr:
                            return True
                except subprocess.TimeoutExpired:
                    pass
                except Exception:
                    pass
                finally:
                    if os.path.exists(tpath):
                        os.unlink(tpath)
                return False

            s_template = template.decode('utf-8', errors='ignore')
            
            # Identify insertion points:
            # 1. Existing hex strings
            # 2. Values in assignments
            
            points = []
            for m in re.finditer(r'0x[0-9a-fA-F]+', s_template):
                points.append((m.start(), m.end(), "0x"))
            
            for m in re.finditer(r'(=|:)\s*([^\s;]+)', s_template):
                points.append((m.start(2), m.end(2), "0x"))
            
            if not points:
                points.append((len(s_template), len(s_template), "0x"))
            
            # Try to crash at each point
            for start, end, prefix in points:
                # Check with large buffer
                probe = s_template[:start] + prefix + "A"*2000 + s_template[end:]
                if check_crash(probe.encode()):
                    # Minimize length
                    l, r = 1, 2000
                    min_len = 2000
                    while l <= r:
                        mid = (l + r) // 2
                        p = s_template[:start] + prefix + "A"*mid + s_template[end:]
                        if check_crash(p.encode()):
                            min_len = mid
                            r = mid - 1
                        else:
                            l = mid + 1
                    
                    return (s_template[:start] + prefix + "A"*min_len + s_template[end:]).encode()

            # Fallback: Raw hex payload
            raw_large = b"0x" + b"A"*2000
            if check_crash(raw_large):
                l, r = 1, 2000
                min_len = 2000
                while l <= r:
                    mid = (l + r) // 2
                    p = b"0x" + b"A"*mid
                    if check_crash(p):
                        min_len = mid
                        r = mid - 1
                    else:
                        l = mid + 1
                return b"0x" + b"A"*min_len

        except Exception:
            pass
        finally:
            shutil.rmtree(work_dir)
            
        return b""