import os
import sys
import struct
import subprocess
import tempfile
import glob
import random
import math
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir_obj = tempfile.TemporaryDirectory()
        work_dir = work_dir_obj.name
        
        # Fallback payload (64 vertices, matches 1032 bytes, resolution 10)
        pi = 3.141592653589793
        poly_64 = []
        for i in range(64):
            angle = 2 * pi * i / 64
            rad = 0.1
            poly_64.append((rad * math.sin(angle), rad * math.cos(angle)))
        
        fallback = struct.pack('<ii', 10, 64)
        for lat, lon in poly_64:
            fallback += struct.pack('<dd', lat, lon)

        try:
            # Extract source
            if src_path.endswith('.tar.gz') or src_path.endswith('.tgz'):
                subprocess.run(['tar', '-xzf', src_path, '-C', work_dir], check=True, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(['tar', '-xf', src_path, '-C', work_dir], check=True, stderr=subprocess.DEVNULL)

            # Find source files and include directory
            h3_src_files = []
            include_dir = ""
            for root, dirs, files in os.walk(work_dir):
                if 'h3api.h' in files:
                    include_dir = root
                if root.endswith("src/h3lib/lib") or root.endswith("src/h3lib/lib/"):
                    for f in files:
                        if f.endswith(".c"):
                            h3_src_files.append(os.path.join(root, f))
            
            if not include_dir:
                h_files = glob.glob(os.path.join(work_dir, "**", "h3api.h"), recursive=True)
                if h_files: include_dir = os.path.dirname(h_files[0])
            
            if not h3_src_files:
                all_c = glob.glob(os.path.join(work_dir, "**", "*.c"), recursive=True)
                h3_src_files = [f for f in all_c if "h3lib" in f and "test" not in f and "app" not in f]
            
            # Determine function names based on API version
            target_func = "polygonToCells"
            max_size_func = "maxPolygonToCellsSize"
            is_v4 = True
            
            if include_dir:
                try:
                    with open(os.path.join(include_dir, 'h3api.h'), 'r') as f:
                        content = f.read()
                        if "polygonToCellsExperimental" in content:
                            target_func = "polygonToCellsExperimental"
                        elif "polyfill" in content:
                            target_func = "polyfill"
                            max_size_func = "maxPolyfillSize"
                            is_v4 = False
                except: pass

            # Create a test driver
            driver_code = """
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include "h3api.h"

int main(int argc, char** argv) {
    if (argc < 2) return 0;
    FILE *f = fopen(argv[1], "rb");
    if (!f) return 0;
    fseek(f, 0, SEEK_END);
    long fsize = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *data = malloc(fsize);
    if (!data) return 0;
    fread(data, 1, fsize, f);
    fclose(f);

    if (fsize < 8) { free(data); return 0; }
    int res = ((int*)data)[0];
    int numVerts = ((int*)data)[1];

    if (numVerts < 3 || numVerts > 200000) { free(data); return 0; }
    if (fsize < 8 + numVerts * 16) { free(data); return 0; }

    GeoCoord *verts = malloc(numVerts * sizeof(GeoCoord));
    if (!verts) { free(data); return 0; }
    double *d_data = (double*)(data + 8);
    for(int i=0; i<numVerts; i++) {
        verts[i].lat = d_data[2*i];
        verts[i].lon = d_data[2*i+1];
    }

    GeoBoundary boundary;
    boundary.numVerts = numVerts;
    boundary.verts = verts;
    
    GeoPolygon polygon;
    polygon.geofence = boundary;
    polygon.numHoles = 0;
    polygon.holes = NULL;

    int64_t size = 0;
#if defined(USE_POLYFILL)
    size = maxPolyfillSize(&polygon, res);
    if (size <= 0) { free(verts); free(data); return 0; }
#else
    H3Error err = maxPolygonToCellsSize(&polygon, res, 0, &size);
    if (err) { free(verts); free(data); return 0; }
#endif

    H3Index *out = malloc(size * sizeof(H3Index));
    if (!out) { free(verts); free(data); return 0; }

#if defined(USE_POLYFILL)
    polyfill(&polygon, res, out);
#elif defined(USE_EXPERIMENTAL)
    polygonToCellsExperimental(&polygon, res, 0, out);
#else
    polygonToCells(&polygon, res, 0, out);
#endif

    free(out);
    free(verts);
    free(data);
    return 0;
}
"""
            macros = []
            if target_func == "polyfill":
                macros.append("-DUSE_POLYFILL")
            elif target_func == "polygonToCellsExperimental":
                macros.append("-DUSE_EXPERIMENTAL")
            
            driver_path = os.path.join(work_dir, "driver.c")
            with open(driver_path, 'w') as f:
                f.write(driver_code)
                
            exe_path = os.path.join(work_dir, "driver")
            cmd = ["clang", "-fsanitize=address", "-O1", f"-I{include_dir}", driver_path] + h3_src_files + ["-o", exe_path] + macros
            
            # Compile
            subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
            
            def make_input(res, verts):
                b = struct.pack('<ii', res, len(verts))
                for lat, lon in verts:
                    b += struct.pack('<dd', lat, lon)
                return b

            # Initial candidates
            candidates = []
            # Transmeridian / Pole cases are common triggers
            candidates.append(make_input(10, poly_64)) # Fallback candidate
            candidates.append(make_input(14, poly_64)) 

            import time
            start = time.time()
            # Fuzz for 45 seconds to find a crash
            while time.time() - start < 45:
                if candidates:
                    data = candidates.pop(0)
                else:
                    # Random fuzzing
                    res = random.randint(4, 15)
                    nv = random.choice([4, 16, 32, 64])
                    vs = []
                    clat = random.uniform(-1.2, 1.2)
                    clon = random.uniform(-3.0, 3.0)
                    rad = random.uniform(0.001, 0.5)
                    for _ in range(nv):
                        vs.append((clat + random.uniform(-rad, rad), clon + random.uniform(-rad, rad)))
                    data = make_input(res, vs)
                
                tf = os.path.join(work_dir, "fuzz.bin")
                with open(tf, 'wb') as f: f.write(data)
                
                try:
                    p = subprocess.run([exe_path, tf], capture_output=True, timeout=1)
                    # ASAN crash detection
                    if p.returncode != 0 and (b"AddressSanitizer" in p.stderr or b"heap-buffer-overflow" in p.stderr):
                        return data
                except: pass
            
            return fallback

        except:
            return fallback
        finally:
            work_dir_obj.cleanup()
