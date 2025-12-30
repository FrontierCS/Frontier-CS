class Solution:
    def solve(self, src_path: str) -> bytes:
        depth = 100
        stream_lines = []
        for i in range(depth):
            w = 612 - i
            h = 792 - i
            stream_lines.append(f'q 0 0 {w} {h} re W n')
        stream_lines.append('0 0 612 792 re f')
        for i in range(depth):
            stream_lines.append('Q')
        stream = b'\n'.join(s.encode('ascii') for s in stream_lines) + b'\n'
        stream_len = len(stream)
        parts = []
        parts.append(b'%PDF-1.4\n')
        obj_starts = {}
        current_offset = len(parts[0])
        obj_starts[1] = current_offset
        parts.append(b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n')
        current_offset += len(parts[-1])
        obj_starts[2] = current_offset
        parts.append(b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n')
        current_offset += len(parts[-1])
        obj_starts[3] = current_offset
        parts.append(b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n')
        current_offset += len(parts[-1])
        obj_starts[4] = current_offset
        length_part = b'4 0 obj\n<< /Length ' + str(stream_len).encode('ascii') + b' >>\nstream\n'
        parts.append(length_part)
        current_offset += len(length_part)
        parts.append(stream)
        current_offset += len(stream)
        parts.append(b'endstream\nendobj\n')
        current_offset += len(parts[-1])
        xref_start = current_offset
        parts.append(b'xref\n0 5\n0000000000 65535 f \n')
        for i in range(1, 5):
            offset_str = f'{obj_starts[i]:010d}'.encode('ascii')
            parts.append(offset_str + b' 00000 n \n')
        trailer = b'''trailer
<< /Size 5 /Root 1 0 R >>
startxref
''' + str(xref_start).encode('ascii') + b'''
%%EOF
'''
        parts.append(trailer)
        return b''.join(parts)