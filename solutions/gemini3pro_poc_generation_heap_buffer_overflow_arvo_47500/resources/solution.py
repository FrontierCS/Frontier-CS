import os
import sys
import subprocess
import tempfile
import shutil
import glob
import random
import struct
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a temporary workspace
        work_dir = tempfile.mkdtemp()
        
        try:
            # Extract source code
            if os.path.isfile(src_path):
                subprocess.run(["tar", "xf", src_path, "-C", work_dir], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                # Locate the extracted directory
                entries = [os.path.join(work_dir, x) for x in os.listdir(work_dir)]
                src_root = next((x for x in entries if os.path.isdir(x)), work_dir)
            else:
                src_root = src_path

            # Build OpenJPEG with ASAN
            build_dir = os.path.join(src_root, "build")
            os.makedirs(build_dir, exist_ok=True)
            
            # Configure
            cmd_cmake = [
                "cmake", "..",
                "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
                "-DCMAKE_C_FLAGS=-fsanitize=address",
                "-DCMAKE_CXX_FLAGS=-fsanitize=address",
                "-DBUILD_SHARED_LIBS=OFF",
                "-DBUILD_CODEC=ON",
                "-DBUILD_THIRDPARTY=OFF",
                "-DBUILD_TESTING=OFF"
            ]
            
            # Compile
            subprocess.run(cmd_cmake, cwd=build_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["make", "-j8"], cwd=build_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Locate executable
            target_bin = os.path.join(build_dir, "bin", "opj_decompress")
            if not os.path.exists(target_bin):
                # Fallback search
                for r, _, f in os.walk(build_dir):
                    if "opj_decompress" in f:
                        target_bin = os.path.join(r, "opj_decompress")
                        break
            
            if not os.path.exists(target_bin):
                # Build failed, return synthetic seed as best effort
                return self.generate_seed()

            # Collect seeds
            seeds = []
            # Look for existing small test files
            for root, _, files in os.walk(src_root):
                for file in files:
                    if file.endswith((".j2k", ".jp2", ".j2c")):
                        full_path = os.path.join(root, file)
                        try:
                            s = os.stat(full_path)
                            if 0 < s.st_size < 50000:
                                with open(full_path, "rb") as f:
                                    seeds.append(f.read())
                        except:
                            pass
            
            # Add synthetic seed
            seeds.append(self.generate_seed())

            # Fuzzing loop
            start_time = time.time()
            timeout = 180  # 3 minutes max
            
            while time.time() - start_time < timeout:
                seed = random.choice(seeds)
                mutated = self.mutate(seed)
                
                with tempfile.NamedTemporaryFile(suffix=".j2k", delete=False) as tmp:
                    tmp.write(mutated)
                    tmp_name = tmp.name
                
                try:
                    # Run target
                    res = subprocess.run(
                        [target_bin, "-i", tmp_name, "-o", os.devnull],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        timeout=2
                    )
                    
                    if res.returncode != 0:
                        err_out = res.stderr.decode(errors="ignore")
                        # Check for ASAN error
                        if "AddressSanitizer" in err_out and "Heap-buffer-overflow" in err_out:
                            os.remove(tmp_name)
                            return mutated
                except subprocess.TimeoutExpired:
                    pass
                finally:
                    if os.path.exists(tmp_name):
                        os.remove(tmp_name)
            
            # Return synthetic seed if no crash found
            return self.generate_seed()

        except Exception:
            return self.generate_seed()
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def generate_seed(self) -> bytes:
        def p32(x): return struct.pack(">I", x)
        def p16(x): return struct.pack(">H", x)
        
        # Construct a J2K codestream with HT markers
        # SOC
        data = b"\xFF\x4F"
        
        # SIZ
        # 513x513 image to trigger potential alignment issues in allocation
        siz = p16(0) + p32(513) + p32(513) + p32(0) + p32(0) + p32(513) + p32(513) + p32(0) + p32(0) + p16(1) + b"\x07\x01\x01"
        data += b"\xFF\x51" + p16(len(siz)+2) + siz
        
        # CAP (Capabilities) - Essential for HTJ2K
        # Pcap = 0x00040000 (arbitrary high bit to encourage extension checks)
        cap = p32(0x00040000) + p16(0xFFFF) 
        data += b"\xFF\x50" + p16(len(cap)+2) + cap
        
        # COD
        # 64x64 blocks
        cod = b"\x00" * 5 + b"\x01\x04\x04\x00\x00"
        data += b"\xFF\x52" + p16(len(cod)+2) + cod
        
        # QCD
        qcd = b"\x00" + b"\x00" * 32
        data += b"\xFF\x5C" + p16(len(qcd)+2) + qcd
        
        # SOD
        data += b"\xFF\x93"
        data += os.urandom(1024)
        
        # EOC
        data += b"\xFF\xD9"
        
        return data

    def mutate(self, data: bytes) -> bytes:
        arr = bytearray(data)
        if not arr: return data
        
        method = random.randint(0, 4)
        if method == 0:
            # Byte flip
            idx = random.randint(0, len(arr)-1)
            arr[idx] = random.randint(0, 255)
        elif method == 1:
            # Bit flip
            idx = random.randint(0, len(arr)-1)
            bit = random.randint(0, 7)
            arr[idx] ^= (1 << bit)
        elif method == 2:
            # Interesting integers (BE)
            if len(arr) > 4:
                idx = random.randint(0, len(arr)-4)
                val = random.choice([0, 1, 0xFFFFFFFF, 0x80000000, 512, 1024, 65535])
                struct.pack_into(">I", arr, idx, val)
        elif method == 3:
            # Interesting shorts (BE)
            if len(arr) > 2:
                idx = random.randint(0, len(arr)-2)
                val = random.choice([0, 1, 0xFFFF, 0x8000])
                struct.pack_into(">H", arr, idx, val)
        elif method == 4:
            # Extension
            arr += os.urandom(random.randint(1, 100))
            
        return bytes(arr)
