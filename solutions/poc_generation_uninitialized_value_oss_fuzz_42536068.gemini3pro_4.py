import os
import sys
import tarfile
import subprocess
import tempfile
import random
import time
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a temporary directory for the build and fuzzing process
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract source code
            try:
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=temp_dir)
            except Exception:
                return b"A" * 2179

            # Identify fuzz target and source files
            fuzz_target_file = None
            sources = []
            includes = set()
            
            for root, dirs, files in os.walk(temp_dir):
                if 'include' in dirs:
                    includes.add(os.path.join(root, 'include'))
                includes.add(root)
                
                for f in files:
                    fp = os.path.join(root, f)
                    if f.endswith(('.c', '.cc', '.cpp', '.cxx')):
                        sources.append(fp)
                        try:
                            with open(fp, 'r', encoding='latin-1') as fh:
                                content = fh.read()
                                if "LLVMFuzzerTestOneInput" in content:
                                    fuzz_target_file = fp
                        except:
                            pass

            if not fuzz_target_file:
                # Fallback if no target found
                return b"A" * 2179

            # Filter source files to compile
            # Exclude tests, examples, and files with main() that are not the target
            compile_srcs = []
            for s in sources:
                if s == fuzz_target_file:
                    compile_srcs.append(s)
                    continue
                
                # Exclude obvious test/example files
                s_lower = s.lower()
                if any(x in s_lower for x in ['test', 'example', 'demo', 'fuzz']):
                    continue
                
                # Check for main()
                try:
                    with open(s, 'r', encoding='latin-1') as fh:
                        if re.search(r'\bint\s+main\s*\(', fh.read()):
                            continue
                except:
                    pass
                
                compile_srcs.append(s)

            # Generate a driver to run the fuzzer
            driver_path = os.path.join(temp_dir, "driver.cpp")
            with open(driver_path, "w") as f:
                f.write("""
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size);
extern "C" { __attribute__((weak)) int LLVMFuzzerInitialize(int *argc, char ***argv); }

int main(int argc, char **argv) {
    if (argc < 2) return 0;
    
    // Call initialization if present
    if (LLVMFuzzerInitialize) {
        LLVMFuzzerInitialize(&argc, &argv);
    }
    
    FILE *f = fopen(argv[1], "rb");
    if (!f) return 0;
    
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    
    uint8_t *data = (uint8_t *)malloc(sz);
    if (data) {
        fread(data, 1, sz, f);
        LLVMFuzzerTestOneInput(data, sz);
        free(data);
    }
    fclose(f);
    return 0;
}
""")

            # Compile the fuzzer
            bin_path = os.path.join(temp_dir, "fuzz_bin")
            include_flags = [f"-I{i}" for i in includes]
            
            # Prioritize MSan for Uninitialized Value detection, fallback to ASan
            sanitizer_configs = [
                ["-fsanitize=memory", "-fsanitize-memory-track-origins"],
                ["-fsanitize=address"]
            ]
            
            built = False
            for sanitizers in sanitizer_configs:
                cmd = ["clang++", "-g", "-O1", "-fno-omit-frame-pointer", "-o", bin_path, driver_path] + \
                      compile_srcs + include_flags + sanitizers
                try:
                    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    built = True
                    break
                except subprocess.CalledProcessError:
                    continue
            
            if not built:
                return b"A" * 2179

            # Harvest tokens/strings from source for dictionary
            tokens = set()
            str_re = re.compile(rb'"([^"]{1,32})"')
            for s in compile_srcs:
                try:
                    with open(s, "rb") as f:
                        for m in str_re.finditer(f.read()):
                            tokens.add(m.group(1))
                except: pass
            vocab = list(tokens)

            # Fuzzing Loop
            corpus = [b"", b"A" * 16] + vocab[:100]
            start_time = time.time()
            max_duration = 45 # seconds
            best_crash = None
            
            while time.time() - start_time < max_duration:
                # Select seed
                seed = random.choice(corpus)
                mutated = bytearray(seed)
                
                # Mutation Strategy
                op = random.randint(0, 3)
                if op == 0: # Flip
                    if mutated:
                        idx = random.randint(0, len(mutated)-1)
                        mutated[idx] ^= random.randint(1, 255)
                elif op == 1: # Insert from vocab
                    ins = random.choice(vocab) if vocab else b"A"
                    pos = random.randint(0, len(mutated))
                    mutated[pos:pos] = ins
                elif op == 2: # Delete
                    if len(mutated) > 1:
                        l = random.randint(1, min(len(mutated), 16))
                        p = random.randint(0, len(mutated)-l)
                        del mutated[p:p+l]
                elif op == 3: # Splicing
                    other = random.choice(corpus)
                    mutated += other
                
                candidate = bytes(mutated)[:4096]
                
                # Write candidate to file
                with tempfile.NamedTemporaryFile(delete=False) as tf:
                    tf.write(candidate)
                    tf_name = tf.name
                
                # Run target
                try:
                    proc = subprocess.run([bin_path, tf_name], capture_output=True, timeout=1.0)
                    
                    # Check for crash (non-zero exit)
                    if proc.returncode != 0:
                        # Prioritize actual Sanitizer errors
                        if b"Sanitizer" in proc.stderr or proc.returncode == 77 or proc.returncode == 1:
                            best_crash = candidate
                            os.remove(tf_name)
                            break
                except subprocess.TimeoutExpired:
                    pass
                except Exception:
                    pass
                
                os.remove(tf_name)
                
                # Update corpus
                if len(corpus) < 500:
                    corpus.append(candidate)

            return best_crash if best_crash else b"A" * 2179
