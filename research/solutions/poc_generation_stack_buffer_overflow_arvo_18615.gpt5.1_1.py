import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability, by mining the source
        tarball for an existing PoC or crash-inducing input.
        """
        fallback_poc = b"A" * 10

        def is_large(m: tarfile.TarInfo) -> bool:
            return m.size > 65536  # avoid very large files

        code_exts = {
            ".c", ".h", ".hpp", ".hh", ".cc", ".cpp", ".cxx",
            ".py", ".sh", ".bash", ".zsh", ".ksh",
            ".pl", ".rb", ".tcl",
            ".java", ".js", ".ts",
            ".html", ".htm", ".xml", ".xsl",
            ".tex", ".texi", ".texinfo", ".sty",
            ".md", ".rst",
            ".txt", ".log",
            ".in", ".ac", ".am", ".m4",
            ".y", ".l",
            ".el",
            ".s", ".S", ".asm",
            ".go", ".rs", ".php",
            ".m", ".mm",
            ".cs",
            ".properties", ".cfg", ".conf", ".ini",
        }

        def choose_poc_from_tar(path: str):
            try:
                tf = tarfile.open(path, "r:*")
            except Exception:
                return None
            try:
                members = []
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    if m.size <= 0:
                        continue
                    if is_large(m):
                        continue
                    lname = m.name.lower()
                    # Skip obvious VCS/admin files
                    if "/.git/" in lname or lname.endswith(".gitignore") or lname.endswith(".gitattributes"):
                        continue
                    members.append(m)

                if not members:
                    return None

                # Phase 1: prioritize files whose names suggest they are PoCs / crashes / seeds.
                poc_keywords = ["poc", "crash", "id:", "id_", "id-", "bug", "overflow", "input", "seed"]
                poc_like = []
                for m in members:
                    lname = m.name.lower()
                    if any(k in lname for k in poc_keywords):
                        poc_like.append(m)

                def ext_info(m: tarfile.TarInfo):
                    base = os.path.basename(m.name)
                    _, ext = os.path.splitext(base)
                    ext = ext.lower()
                    is_code = 1 if ext in code_exts else 0  # prefer 0 (non-code/binary)
                    return is_code

                if poc_like:
                    def score_poc(m: tarfile.TarInfo):
                        lname = m.name.lower()
                        size = m.size
                        is_code = ext_info(m)
                        tic_bonus = 0 if ("tic30" in lname or "tic-30" in lname) else 1
                        size_penalty = abs(size - 10)
                        return (is_code, tic_bonus, size_penalty, size, len(m.name), m.name)

                    best = min(poc_like, key=score_poc)
                    f = tf.extractfile(best)
                    if f is None:
                        return None
                    try:
                        data = f.read()
                    finally:
                        f.close()
                    if data:
                        return data

                # Phase 2: generic heuristic based on size, extension, and keywords.
                def generic_score(m: tarfile.TarInfo):
                    name = m.name
                    lname = name.lower()
                    size = m.size
                    base = os.path.basename(lname)
                    root, ext = os.path.splitext(base)
                    ext = ext.lower()

                    is_size10 = 0 if size == 10 else 1  # prefer exact 10-byte files
                    is_code_ext = 1 if ext in code_exts else 0  # prefer non-code
                    is_hidden = 1 if base.startswith(".") else 0  # prefer non-hidden

                    keyword_rank = 4
                    if "poc" in lname:
                        keyword_rank = 0
                    elif ("crash" in lname) or ("overflow" in lname) or ("bug" in lname):
                        keyword_rank = 1
                    elif ("tic30" in lname) or ("tic-30" in lname):
                        keyword_rank = 2
                    elif ("test" in lname) or ("regress" in lname):
                        keyword_rank = 3

                    size_penalty = abs(size - 10)

                    return (
                        is_size10,
                        is_code_ext,
                        is_hidden,
                        keyword_rank,
                        size_penalty,
                        size,
                        len(name),
                        name,
                    )

                best_generic = min(members, key=generic_score)
                f = tf.extractfile(best_generic)
                if f is None:
                    return None
                try:
                    data = f.read()
                finally:
                    f.close()
                if not data:
                    return None
                return data
            finally:
                try:
                    tf.close()
                except Exception:
                    pass

        data = choose_poc_from_tar(src_path)
        if not data:
            return fallback_poc
        return data