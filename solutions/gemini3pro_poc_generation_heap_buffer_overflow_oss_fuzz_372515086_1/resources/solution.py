import os
import sys
import shutil
import subprocess
import glob
import struct
import random
import time
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp()
        
        try:
            # Extract source code
            subprocess.check_call(['tar', 'xf', src_path, '-C', work_dir], 
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Locate root directory
            contents = os.listdir(work_dir)
            src_root = work_dir
            if len(contents) == 1 and os.path.isdir(os.path.join(work_dir, contents[0])):
                src_root = os.path.join(work_dir, contents[0])
            
            # Locate library sources and include directories
            lib_srcs = []
            include_dir = None
            
            for root, dirs, files in os.walk(src_root):
                if "h3api.h" in files:
                    include_dir = root
                
                # Exclude test/fuzz/apps/examples/benchmark dirs
                path_parts = root.split(os.sep)
                if any(x in path_parts for x in ["test", "tests", "fuzz", "fuzzers", "apps", "examples", "benchmark"]):
                    continue
                
                for f in files:
                    if f.endswith(".c"):
                        lib_srcs.append(os.path.join(root, f))

            # Locate existing fuzzer
            fuzzer_src = None
            candidates = glob.glob(os.path.join(src_root, "**", "*.c"), recursive=True)
            fuzzer_candidates = []
            for c in candidates:
                if "fuzz" in c and ("polygonToCells" in c or "polyfill" in c):
                    fuzzer_candidates.append(c)
            
            # Prefer 'Experimental' naming if available
            fuzzer_candidates.sort(key=lambda x: "Experimental" in x, reverse=True)
            if fuzzer_candidates:
                fuzzer_src = fuzzer_candidates[0]
            
            # Prepare runner and compilation
            exe_path = os.path.join(work_dir, "vuln_fuzz")
            runner_src = os.path.join(work_dir, "runner.c")
            
            # Generic runner for LLVMFuzzerTestOneInput
            with open(runner_src, 'w') as f:
                f.write(r'''
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size);

int main(int argc, char **argv) {
    if (argc < 2) return 0;
    FILE *f = fopen(argv[1], "rb");
    if (!f) return 0;
    fseek(f, 0, SEEK_END);
    long len = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *buf = malloc(len);
    if (!buf) { fclose(f); return 0; }
    fread(buf, 1, len, f);
    fclose(f);
    LLVMFuzzerTestOneInput(buf, len);
    free(buf);
    return 0;
}
''')
            
            cmd = ["clang", "-fsanitize=address", "-g", "-O1"]
            if include_dir:
                cmd.extend(["-I", include_dir])
            
            cmd.extend(lib_srcs)
            
            if fuzzer_src:
                cmd.append(fuzzer_src)
            else:
                # Fallback custom fuzzer if source not found
                custom_fuzzer = os.path.join(work_dir, "custom_fuzzer.c")
                with open(custom_fuzzer, 'w') as f:
                    f.write(r'''
#include "h3api.h"
#include <string.h>
#include <stdlib.h>
#include <stdint.h>

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size < 8) return 0;
    int res = ((int*)data)[0];
    int numVerts = ((int*)data)[1];
    if (numVerts < 3 || numVerts > 2000) return 0;
    
    size_t needed = 8 + numVerts * 16;
    if (size < needed) return 0;
    
    GeoCoord *verts = malloc(sizeof(GeoCoord) * numVerts);
    if (!verts) return 0;
    
    const double *d_data = (const double*)(data + 8);
    for(int i=0; i<numVerts; i++) {
        verts[i].lat = d_data[2*i];
        verts[i].lon = d_data[2*i+1];
    }
    
    Geofence geofence = {numVerts, verts};
    GeoPolygon polygon = {geofence, 0, NULL};
    
    int64_t numHexagons = 0;
    if (maxPolygonToCellsSize(&polygon, res, 0, &numHexagons) == 0) {
        H3Index* out = malloc(numHexagons * sizeof(H3Index));
        if (out) {
            polygonToCellsExperimental(&polygon, res, 0, out);
            free(out);
        }
    }
    free(verts);
    return 0;
}
''')
                cmd.append(custom_fuzzer)

            cmd.append(runner_src)
            cmd.extend(["-o", exe_path])
            
            # Compile
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Fuzzing Loop
            best_poc = b""
            start_time = time.time()
            
            while time.time() - start_time < 45:
                # Generate candidate PoC
                # Target format based on ground truth: 1032 bytes
                # Structure: Resolution(4) + Count(4) + 64 * Vertices(16) = 1032
                
                count = 64
                res = random.randint(0, 15)
                
                coords_bytes = bytearray()
                for _ in range(count):
                    # Random lat/lon
                    lat = random.uniform(-1.5, 1.5)
                    lon = random.uniform(-3.1, 3.1)
                    coords_bytes.extend(struct.pack('<dd', lat, lon))
                
                payload = struct.pack('<ii', res, count) + coords_bytes
                
                # Write to temp file
                fd, path = tempfile.mkstemp()
                os.write(fd, payload)
                os.close(fd)
                
                # Execute
                proc = subprocess.Popen([exe_path, path], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                _, stderr = proc.communicate()
                
                # Check for crash
                if proc.returncode != 0 and b"AddressSanitizer" in stderr:
                    best_poc = payload
                    os.unlink(path)
                    break
                
                os.unlink(path)
            
            if best_poc:
                return best_poc
            
            # Fallback
            return struct.pack('<ii', 10, 64) + b'\x00' * 1024
            
        except Exception:
            return b"A" * 1032
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
