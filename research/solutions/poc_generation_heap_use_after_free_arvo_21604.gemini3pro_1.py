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
        work_dir = tempfile.mkdtemp()
        try:
            # Extract source code
            if src_path.endswith('.tar.gz') or src_path.endswith('.tgz'):
                with tarfile.open(src_path, "r:gz") as tar:
                    tar.extractall(work_dir)
            elif src_path.endswith('.tar.xz'):
                with tarfile.open(src_path, "r:xz") as tar:
                    tar.extractall(work_dir)
            elif src_path.endswith('.tar'):
                with tarfile.open(src_path, "r:") as tar:
                    tar.extractall(work_dir)
            else:
                try:
                    with tarfile.open(src_path, "r") as tar:
                        tar.extractall(work_dir)
                except:
                    pass

            # Locate Makefile and source root
            src_root = work_dir
            for root, dirs, files in os.walk(work_dir):
                if "Makefile" in files:
                    src_root = root
                    break

            # Compile mupdf
            # We attempt to build it to use it for fuzzing.
            # Using -j8 to utilize available vCPUs.
            try:
                subprocess.run(["make", "-j8"], cwd=src_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
            except:
                pass

            # Locate mutool binary
            mutool_path = None
            for root, dirs, files in os.walk(src_root):
                if "mutool" in files:
                    candidate = os.path.join(root, "mutool")
                    if os.access(candidate, os.X_OK):
                        mutool_path = candidate
                        break

            # Construct a base seed that targets Form/Widget structures based on the vulnerability description
            # "destruction of standalone forms where passing the Dict to Object()..."
            seed = (
                b"%PDF-1.7\n"
                b"1 0 obj\n"
                b"<< /Type /Catalog /Pages 2 0 R /AcroForm << /Fields [4 0 R] >> >>\n"
                b"endobj\n"
                b"2 0 obj\n"
                b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
                b"endobj\n"
                b"3 0 obj\n"
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Annots [4 0 R] >>\n"
                b"endobj\n"
                b"4 0 obj\n"
                b"<< /Type /Annot /Subtype /Widget /Rect [10 10 100 100] /T (Test) /FT /Tx >>\n"
                b"endobj\n"
                b"xref\n"
                b"0 5\n"
                b"0000000000 65535 f \n"
                b"0000000010 00000 n \n"
                b"0000000079 00000 n \n"
                b"0000000135 00000 n \n"
                b"0000000223 00000 n \n"
                b"trailer\n"
                b"<< /Size 5 /Root 1 0 R >>\n"
                b"startxref\n"
                b"320\n"
                b"%%EOF\n"
            )

            if not mutool_path:
                return seed

            # Collect other seeds from source code directories if available
            seeds = [seed]
            for root, dirs, files in os.walk(src_root):
                for f in files:
                    if f.endswith(".pdf"):
                        try:
                            with open(os.path.join(root, f), "rb") as fp:
                                seeds.append(fp.read())
                        except:
                            pass
                if len(seeds) > 20:
                    break

            def mutate(data):
                if len(data) < 10: return data
                res = bytearray(data)
                # Apply 1 to 3 mutations
                for _ in range(random.randint(1, 3)):
                    algo = random.randint(0, 5)
                    if algo == 0: # Byte Flip
                        idx = random.randint(0, len(res)-1)
                        res[idx] ^= 0xFF
                    elif algo == 1: # Insert keywords related to issue
                        idx = random.randint(0, len(res))
                        res[idx:idx] = b" /Dict /Object /Form "
                    elif algo == 2: # Delete chunk
                        if len(res) > 5:
                            start = random.randint(0, len(res)-5)
                            del res[start:start+random.randint(1, 10)]
                    elif algo == 3: # Random byte overwrite
                        idx = random.randint(0, len(res)-1)
                        res[idx] = random.randint(0, 255)
                    elif algo == 4: # Duplicate chunk
                        if len(res) > 10:
                            start = random.randint(0, len(res)-10)
                            length = random.randint(1, 10)
                            res[start:start] = res[start:start+length]
                    elif algo == 5: # Swap chunks
                        if len(res) > 20:
                            p1 = random.randint(0, len(res)-10)
                            p2 = random.randint(0, len(res)-10)
                            chunk = res[p1:p1+5]
                            res[p1:p1+5] = res[p2:p2+5]
                            res[p2:p2+5] = chunk
                return bytes(res)

            # Fuzz loop
            start_t = time.time()
            queue = list(seeds)
            
            # Run for up to 120 seconds or until crash
            while time.time() - start_t < 120:
                if not queue:
                    for _ in range(20):
                        queue.append(mutate(random.choice(seeds)))
                
                curr = queue.pop(0)
                tf = os.path.join(work_dir, "fuzz.pdf")
                with open(tf, "wb") as f:
                    f.write(curr)
                
                # Check for crash using mutool draw (renders page, triggers parsing)
                try:
                    # Ignore stdout, pipe stderr for ASAN detection
                    p = subprocess.run(
                        [mutool_path, "draw", "-o", "/dev/null", tf],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        timeout=2
                    )
                    
                    # Return code < 0 indicates signal (crash)
                    if p.returncode < 0:
                        return curr
                    
                    # If return code is non-zero, check stderr for sanitizer errors
                    if p.returncode != 0:
                        err = p.stderr.decode(errors='ignore')
                        if "Sanitizer" in err or "use-after-free" in err or "AddressSanitizer" in err:
                            return curr
                            
                except subprocess.TimeoutExpired:
                    pass
                except Exception:
                    pass
            
            return seed

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)