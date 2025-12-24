import os
import sys
import tarfile
import subprocess
import tempfile
import time
import random
import glob
from concurrent.futures import ThreadPoolExecutor

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        work_dir_obj = tempfile.TemporaryDirectory()
        work_dir = work_dir_obj.name
        
        # Extract source code
        try:
            if src_path.endswith('.tar.gz') or src_path.endswith('.tgz'):
                with tarfile.open(src_path, "r:gz") as tar:
                    tar.extractall(path=work_dir)
            elif src_path.endswith('.tar'):
                with tarfile.open(src_path, "r:") as tar:
                    tar.extractall(path=work_dir)
            else:
                # Assuming directory or other format not handled, try simple copy if needed
                pass
        except Exception:
            return b""

        # Locate fuzz target (file with LLVMFuzzerTestOneInput)
        fuzz_file = None
        for root, _, files in os.walk(work_dir):
            for f in files:
                if f.endswith(('.c', '.cc', '.cpp')):
                    path = os.path.join(root, f)
                    try:
                        with open(path, 'r', errors='ignore') as fp:
                            if "LLVMFuzzerTestOneInput" in fp.read():
                                fuzz_file = path
                                break
                    except:
                        pass
            if fuzz_file:
                break
        
        if not fuzz_file:
            return b"v=0\r\no=- 0 0 IN IP4 0.0.0.0\r\ns=-\r\nt=0 0\r\n"

        is_cpp = fuzz_file.endswith(('.cc', '.cpp'))
        compiler = "clang++" if is_cpp else "clang"
        fuzz_dir = os.path.dirname(fuzz_file)
        
        # Heuristic to find relevant source files and include directories
        # We start from the fuzz target directory and go up a few levels to capture 'core', 'parser', etc.
        source_files = []
        include_dirs = set()
        
        # Define directories to scan
        dirs_to_scan = [fuzz_dir]
        parent = os.path.dirname(fuzz_dir)
        if parent and parent != work_dir:
            dirs_to_scan.append(parent)
            grandparent = os.path.dirname(parent)
            if grandparent and grandparent != work_dir:
                dirs_to_scan.append(grandparent)
        
        # Also look for a 'core' directory specifically if we are in a larger repo
        for root, dirs, files in os.walk(work_dir):
            if os.path.basename(root) == 'core':
                dirs_to_scan.append(root)

        seen_files = set()
        
        for d in dirs_to_scan:
            # Walk strictly within this directory (recursive or flat?)
            # Let's do recursive scan of selected dirs
            for root, _, files in os.walk(d):
                include_dirs.add(root)
                for f in files:
                    if f.endswith(('.c', '.cc', '.cpp')):
                        full_path = os.path.join(root, f)
                        if full_path == fuzz_file: continue
                        if full_path in seen_files: continue
                        
                        # Exclude files with main() to avoid link errors
                        try:
                            with open(full_path, 'r', errors='ignore') as fp:
                                content = fp.read()
                                if " int main(" in content or "int main (" in content:
                                    continue
                        except:
                            continue
                        
                        source_files.append(full_path)
                        seen_files.add(full_path)

        # Create a wrapper for the fuzz target
        wrapper_path = os.path.join(work_dir, "fuzz_wrapper.cpp" if is_cpp else "fuzz_wrapper.c")
        with open(wrapper_path, "w") as f:
            if is_cpp:
                f.write('#include <cstdint>\n#include <cstddef>\n#include <cstdio>\n#include <cstdlib>\n')
                f.write('extern "C" int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size);\n')
            else:
                f.write('#include <stdint.h>\n#include <stddef.h>\n#include <stdio.h>\n#include <stdlib.h>\n')
                f.write('int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size);\n')
            
            f.write("""
int main(int argc, char **argv) {
    if (argc > 1) {
        FILE *fp = fopen(argv[1], "rb");
        if(fp){
            fseek(fp, 0, SEEK_END); long sz = ftell(fp); fseek(fp, 0, SEEK_SET);
            uint8_t *buf = (uint8_t*)malloc(sz); 
            if(buf) {
                fread(buf, 1, sz, fp); 
                LLVMFuzzerTestOneInput(buf, sz); 
                free(buf);
            }
            fclose(fp);
        }
    } else {
        uint8_t buf[65536]; 
        size_t n = fread(buf, 1, sizeof(buf), stdin);
        LLVMFuzzerTestOneInput(buf, n);
    }
    return 0;
}
            """)
        
        source_files.append(fuzz_file)
        source_files.append(wrapper_path)

        # Compile
        exe_path = os.path.join(work_dir, "fuzz_bin")
        cmd = [compiler, "-fsanitize=address", "-g", "-O1", "-o", exe_path]
        for inc in include_dirs:
            cmd.append(f"-I{inc}")
        cmd.extend(source_files)
        
        try:
            # Suppress output
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            # If compilation fails, we can't fuzz. Return a generic SDP.
            return b"v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=Session\r\nt=0 0\r\n"

        # Seeds
        seeds = [
            b"v=0\r\no=- 123456 123456 IN IP4 127.0.0.1\r\ns=Session\r\nc=IN IP4 127.0.0.1\r\nt=0 0\r\nm=audio 8000 RTP/AVP 0\r\na=rtpmap:0 PCMU/8000\r\n",
            b"v=0\r\no=jdoe 2890844526 2890842807 IN IP4 10.47.16.5\r\ns=SDP Seminar\r\ni=A Seminar on the session description protocol\r\nu=http://www.example.com/seminars/sdp.pdf\r\ne=j.doe@example.com (Jane Doe)\r\nc=IN IP4 224.2.17.12/127\r\nt=2873397496 2873404696\r\na=recvonly\r\nm=audio 49170 RTP/AVP 0\r\nm=video 51372 RTP/AVP 99\r\na=rtpmap:99 h263-1998/90000\r\n"
        ]

        result_poc = None
        start_time = time.time()
        
        def fuzz_task(tid):
            nonlocal result_poc
            rng = random.Random(tid + start_time)
            
            while time.time() - start_time < 45 and result_poc is None:
                base = rng.choice(seeds)
                mutant = bytearray(base)
                
                # Apply mutations
                num_mutations = rng.randint(1, 10)
                for _ in range(num_mutations):
                    if not mutant: 
                        mutant = bytearray(b"v=0\r\n")
                        break
                    op = rng.randint(0, 5)
                    if op == 0: # Flip bit
                        idx = rng.randint(0, len(mutant)-1)
                        mutant[idx] ^= (1 << rng.randint(0, 7))
                    elif op == 1: # Insert random
                        idx = rng.randint(0, len(mutant))
                        mutant.insert(idx, rng.randint(0, 255))
                    elif op == 2: # Delete
                        idx = rng.randint(0, len(mutant)-1)
                        del mutant[idx]
                    elif op == 3: # Chunk repeat/splice
                        if len(mutant) > 4:
                            start = rng.randint(0, len(mutant)-2)
                            end = rng.randint(start+1, len(mutant))
                            chunk = mutant[start:end]
                            pos = rng.randint(0, len(mutant))
                            mutant[pos:pos] = chunk
                    elif op == 4: # Interesting values
                        vals = [b'\r', b'\n', b'\0', b' ', b':', b'=', b'-1', b'2147483648', b'a=', b'm=']
                        val = rng.choice(vals)
                        pos = rng.randint(0, len(mutant))
                        mutant[pos:pos] = val
                    elif op == 5: # Truncate
                         if len(mutant) > 1:
                            new_len = rng.randint(1, len(mutant))
                            mutant = mutant[:new_len]

                # Execution
                try:
                    proc = subprocess.run([exe_path], input=mutant, capture_output=True, timeout=0.5)
                    if proc.returncode != 0:
                        # Check for ASAN error in stderr
                        if b"AddressSanitizer" in proc.stderr or proc.returncode == -6: # SIGABRT
                            result_poc = bytes(mutant)
                            return
                except:
                    pass
        
        # Parallel Fuzzing
        with ThreadPoolExecutor(max_workers=8) as executor:
            for i in range(8):
                executor.submit(fuzz_task, i)
        
        if result_poc:
            return result_poc
        
        return seeds[0]
