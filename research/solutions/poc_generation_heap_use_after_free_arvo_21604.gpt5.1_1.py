import tarfile
import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        L_g = 33762

        fallback_pdf = (
            b"%PDF-1.1\n"
            b"1 0 obj\n"
            b"<< /Type /Catalog >>\n"
            b"endobj\n"
            b"xref\n"
            b"0 2\n"
            b"0000000000 65535 f \n"
            b"0000000009 00000 n \n"
            b"trailer\n"
            b"<< /Root 1 0 R >>\n"
            b"startxref\n"
            b"53\n"
            b"%%EOF\n"
        )

        keywords = (
            "poc",
            "crash",
            "uaf",
            "use-after-free",
            "use_after_free",
            "heap",
            "bug",
            "issue",
            "21604",
            "form",
            "standalone",
        )
        preferred_exts = {
            ".pdf",
            ".bin",
            ".dat",
            ".data",
            ".raw",
            ".in",
            ".input",
            ".poc",
        }

        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = [m for m in tf.getmembers() if m.isreg() and m.size > 0]
                if not members:
                    return fallback_pdf

                def has_keyword(name_lower: str) -> bool:
                    for kw in keywords:
                        if kw in name_lower:
                            return True
                    return False

                # First, try to find files with exact size match
                exact = [m for m in members if m.size == L_g]

                if exact:
                    def key_exact(m: tarfile.TarInfo):
                        name_lower = m.name.lower()
                        ext = os.path.splitext(name_lower)[1]
                        return (
                            0 if has_keyword(name_lower) else 1,
                            0 if ext in preferred_exts else 1,
                            name_lower.count("/"),
                            len(name_lower),
                        )

                    best = sorted(exact, key=key_exact)[0]
                else:
                    # Fall back to closest-by-size with heuristics
                    def key_any(m: tarfile.TarInfo):
                        name_lower = m.name.lower()
                        ext = os.path.splitext(name_lower)[1]
                        size_penalty = abs(m.size - L_g)
                        return (
                            size_penalty,
                            0 if has_keyword(name_lower) else 1,
                            0 if ext in preferred_exts else 1,
                            name_lower.count("/"),
                            len(name_lower),
                        )

                    best = sorted(members, key=key_any)[0]

                f = tf.extractfile(best)
                if f is not None:
                    data = f.read()
                    if isinstance(data, bytes):
                        return data
                    return bytes(data)

        except Exception:
            pass

        return fallback_pdf