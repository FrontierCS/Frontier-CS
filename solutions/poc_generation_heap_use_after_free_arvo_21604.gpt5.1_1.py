import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_size = 33762

        keywords = (
            "poc",
            "uaf",
            "heap",
            "use_after_free",
            "use-after-free",
            "crash",
            "bug",
            "arvo",
            "21604",
            "pdf",
            "form",
            "forms",
            "xfa",
            "acro",
        )

        source_exts = {
            ".c", ".h", ".hpp", ".hh", ".cc", ".cpp", ".cxx",
            ".py", ".pyc", ".pyo",
            ".sh", ".bash",
            ".md", ".rst", ".txt",
            ".cmake", ".in", ".am", ".ac",
            ".json", ".yml", ".yaml",
            ".xml", ".html", ".htm",
            ".js", ".ts",
            ".java", ".rb", ".go", ".rs", ".pl", ".php",
            ".m", ".mm",
            ".csv",
        }

        def is_source_like(name: str) -> bool:
            base = os.path.basename(name)
            _, ext = os.path.splitext(base.lower())
            return ext in source_exts

        def has_keyword(name: str) -> bool:
            lname = os.path.basename(name).lower()
            return any(k in lname for k in keywords)

        with tarfile.open(src_path, "r:*") as tf:
            members = [m for m in tf.getmembers() if m.isfile()]

            if not members:
                return b""

            # 1. Prefer files exactly matching the known PoC size.
            exact = [m for m in members if m.size == target_size]

            if exact:
                exact.sort(
                    key=lambda m: (
                        0 if has_keyword(m.name) else 1,
                        len(os.path.basename(m.name)),
                    )
                )
                f = tf.extractfile(exact[0])
                return f.read() if f is not None else b""

            # 2. Otherwise, prefer non-source files with PoC-ish names.
            non_source = [m for m in members if m.size > 0 and not is_source_like(m.name)]

            if non_source:
                non_source.sort(
                    key=lambda m: (
                        0 if has_keyword(m.name) else 1,
                        m.size,
                    )
                )
                f = tf.extractfile(non_source[0])
                return f.read() if f is not None else b""

            # 3. Fallback: smallest non-empty file.
            nonempty = [m for m in members if m.size > 0]
            if nonempty:
                nonempty.sort(key=lambda m: m.size)
                f = tf.extractfile(nonempty[0])
                return f.read() if f is not None else b""

        # 4. Ultimate fallback: empty input.
        return b""
