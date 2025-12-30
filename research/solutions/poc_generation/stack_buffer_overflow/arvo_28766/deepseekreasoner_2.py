import os
import sys
import tempfile
import tarfile
import subprocess
import multiprocessing
import random
import struct
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir_path)
            
            # Look for a sample input file
            sample_input = self._find_sample_input(tmpdir_path)
            if sample_input:
                # Try to modify it to trigger the bug
                poc = self._modify_sample(sample_input)
                if poc:
                    return poc
            
            # Otherwise, try to compile and fuzz
            poc = self._compile_and_fuzz(tmpdir_path)
            if poc:
                return poc
            
            # Fallback: 140 bytes of a pattern that might cause issues
            return b'A' * 140
    
    def _find_sample_input(self, root: Path) -> bytes:
        exts = ['.bin', '.dat', '.input', '.snapshot', '.in']
        for ext in exts:
            for path in root.rglob('*' + ext):
                try:
                    data = path.read_bytes()
                    if 0 < len(data) <= 1024:  # reasonable size
                        return data
                except:
                    pass
        return None
    
    def _modify_sample(self, sample: bytes) -> bytes:
        # Try to interpret as little-endian 4-byte integers
        # Assume the sample has at least one node and one reference.
        # We'll attempt to change a referenced node ID to an unused one.
        # This is a heuristic; may not work for all formats.
        if len(sample) < 8:
            return None
        # Try to find a 4-byte integer that looks like a node ID (non-zero, maybe small)
        # We'll just change the last 4 bytes to a large number (e.g., 0xFFFFFFFF)
        # and hope it becomes an invalid reference.
        # But we must keep length exactly 140 if sample is 140.
        if len(sample) == 140:
            # Keep the same length, modify some bytes in the middle.
            # We'll change bytes 100..103 to a large ID.
            ba = bytearray(sample)
            ba[100:104] = struct.pack('<I', 0xFFFFFFF)
            return bytes(ba)
        return None
    
    def _compile_and_fuzz(self, root: Path) -> bytes:
        # Try to find the main source file
        main_file = None
        for suffix in ['.cpp', '.c', '.cc']:
            for path in root.rglob('*' + suffix):
                content = path.read_text(errors='ignore')
                if 'int main(' in content or 'void main(' in content:
                    main_file = path
                    break
            if main_file:
                break
        
        if not main_file:
            # Try to find a Makefile or CMakeLists.txt
            makefile = root / 'Makefile'
            cmake = root / 'CMakeLists.txt'
            if makefile.exists() or cmake.exists():
                # Try to run make
                try:
                    subprocess.run(['make', '-C', str(root)], check=True, capture_output=True, timeout=30)
                except:
                    pass
                # Look for an executable
                for exe in root.rglob('*'):
                    if exe.is_file() and os.access(exe, os.X_OK):
                        # Possibly the compiled binary
                        binary = exe
                        break
                if binary:
                    return self._fuzz_binary(binary)
            return None
        
        # Compile the main file with sanitizers
        binary_path = root / 'processor'
        try:
            # Find all .cpp files
            cpp_files = list(root.rglob('*.cpp')) + list(root.rglob('*.c')) + list(root.rglob('*.cc'))
            cmd = ['g++', '-fsanitize=address,undefined', '-o', str(binary_path)]
            cmd.extend([str(f) for f in cpp_files])
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        except:
            # Try without sanitizers
            try:
                cmd = ['g++', '-o', str(binary_path)]
                cmd.extend([str(f) for f in cpp_files])
                subprocess.run(cmd, check=True, capture_output=True, timeout=60)
            except:
                return None
        
        if binary_path.exists():
            return self._fuzz_binary(binary_path)
        return None
    
    def _fuzz_binary(self, binary: Path) -> bytes:
        # Determine if binary takes file argument or stdin
        # Run with no arguments and see if it hangs (stdin) or prints usage
        try:
            proc = subprocess.run([str(binary)], input=b'', timeout=1, capture_output=True)
            # If it returns quickly, it might expect a file argument
            use_stdin = False
        except subprocess.TimeoutExpired:
            use_stdin = True
        
        # Fuzz with structured inputs of length 140
        def generate_input():
            # We'll generate a few structured candidates:
            # 1. Zero nodes, one reference.
            # 2. One node, one reference to non-existent node.
            # 3. Multiple nodes, one invalid reference.
            # All padded to 140 bytes.
            base = random.randint(0, 2)
            if base == 0:
                # Format: node_count (4), node_list, ref_count (4), ref_list
                node_count = 0
                ref_count = 1
                # Each reference: from_id, to_id (4 bytes each)
                # No nodes, so total so far: 4 + 4 + 8 = 16 bytes
                # Pad with zeros to 140
                data = struct.pack('<IIII', node_count, ref_count, 0, 0xFFFFFFFF)
                data += b'\x00' * (140 - len(data))
                return data
            elif base == 1:
                # One node with ID 1, data of some size, then reference to ID 2
                node_count = 1
                node_id = 1
                # Assume node data is 100 bytes of zeros
                node_data_size = 100
                ref_count = 1
                ref_from = 1
                ref_to = 2  # non-existent
                # Pack: node_count, node_id, data_size, data, ref_count, ref_from, ref_to
                data = struct.pack('<III', node_count, node_id, node_data_size)
                data += b'\x00' * node_data_size
                data += struct.pack('<III', ref_count, ref_from, ref_to)
                # Trim or pad to 140
                if len(data) > 140:
                    data = data[:140]
                else:
                    data += b'\x00' * (140 - len(data))
                return data
            else:
                # Two nodes, reference from first to third (invalid)
                node_count = 2
                node1_id = 1
                node2_id = 2
                data_size = 40  # each node has 40 bytes data
                ref_count = 1
                ref_from = 1
                ref_to = 3
                data = struct.pack('<I', node_count)
                data += struct.pack('<I', node1_id) + b'\x00' * data_size
                data += struct.pack('<I', node2_id) + b'\x00' * data_size
                data += struct.pack('<III', ref_count, ref_from, ref_to)
                if len(data) > 140:
                    data = data[:140]
                else:
                    data += b'\x00' * (140 - len(data))
                return data
        
        def test_input(inp: bytes) -> bool:
            try:
                if use_stdin:
                    proc = subprocess.run([str(binary)], input=inp, capture_output=True, timeout=1)
                else:
                    with tempfile.NamedTemporaryFile() as f:
                        f.write(inp)
                        f.flush()
                        proc = subprocess.run([str(binary), f.name], capture_output=True, timeout=1)
                # Crash if return code non-zero and stderr contains sanitizer error or segmentation fault
                if proc.returncode != 0:
                    err = proc.stderr.decode('utf-8', errors='ignore')
                    if 'ERROR: AddressSanitizer' in err or 'Segmentation fault' in err or 'stack-overflow' in err:
                        return True
                return False
            except subprocess.TimeoutExpired:
                return False
            except Exception:
                return False
        
        # Try a limited number of generations in parallel
        pool = multiprocessing.Pool(processes=8)
        for _ in range(1000):
            inputs = [generate_input() for _ in range(100)]
            results = pool.map(test_input, inputs)
            for inp, crash in zip(inputs, results):
                if crash:
                    pool.terminate()
                    return inp
        pool.terminate()
        return None