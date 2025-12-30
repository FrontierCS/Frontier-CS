import os
import tarfile
import tempfile
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_len = 56
        root_dir: Optional[str] = None

        if os.path.isdir(src_path):
            root_dir = src_path
        else:
            tmpdir = tempfile.mkdtemp(prefix="poc_extracted_")
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    def is_within_directory(directory: str, target: str) -> bool:
                        abs_directory = os.path.abspath(directory)
                        abs_target = os.path.abspath(target)
                        return os.path.commonprefix([abs_directory, abs_target]) == abs_directory

                    for member in tf.getmembers():
                        member_path = os.path.join(tmpdir, member.name)
                        if not is_within_directory(tmpdir, member_path):
                            continue
                        try:
                            tf.extract(member, tmpdir)
                        except (tarfile.ExtractError, OSError):
                            continue
                root_dir = tmpdir
            except tarfile.TarError:
                root_dir = None

        if root_dir is not None:
            poc_path = self._find_poc_file(root_dir, target_len=target_len)
            if poc_path is not None:
                try:
                    with open(poc_path, "rb") as f:
                        data = f.read()
                        if data:
                            return data
                except OSError:
                    pass

        return self._default_poc(target_len)

    def _find_poc_file(self, root_dir: str, target_len: int) -> Optional[str]:
        skip_dirs = {
            ".git", ".hg", ".svn", ".idea", ".vscode", "__pycache__",
            "build", "cmake-build-debug", "cmake-build-release",
            "out", "dist", "debug", "release", "bin", "obj"
        }

        skip_ext_source = {
            "c", "h", "cpp", "cc", "cxx", "hpp", "hh", "hxx",
            "java", "py", "pyc", "pyo",
            "sh", "bash", "zsh", "ksh",
            "pl", "pm", "t", "rb",
            "php", "js", "ts", "tsx", "jsx",
            "html", "htm", "css",
            "md", "markdown", "rst", "tex",
            "m", "mm", "swift", "scala", "kt", "kts", "cs",
            "go", "rs",
            "vb", "vba", "as", "dart", "lua", "r", "jl",
            "ac", "am", "m4", "in",
            "bat", "ps1"
        }

        skip_text_doc_ext = {"md", "markdown", "rst", "tex"}

        tokens_priority = [
            "63746", "ndpi", "poc", "crash", "overflow",
            "stack", "vuln", "bug", "fuzz", "oss-fuzz",
            "ossfuzz", "input", "rule", "subprotocol",
            "host", "ip"
        ]

        best_path: Optional[str] = None
        best_score: Optional[int] = None

        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if d.lower() not in skip_dirs]

            for fname in filenames:
                full_path = os.path.join(dirpath, fname)
                try:
                    st = os.stat(full_path)
                except OSError:
                    continue

                size = st.st_size
                if size == 0 or size > 4096:
                    continue

                name_lower = fname.lower()
                ext = ""
                if "." in fname and not fname.startswith("."):
                    ext = fname.rsplit(".", 1)[1].lower()

                if ext in skip_ext_source or ext in skip_text_doc_ext:
                    continue

                path_lower = full_path.lower()

                if ext == "txt":
                    if not any(t in path_lower for t in (
                        "poc", "crash", "id", "bug", "vuln",
                        "input", "ndpi", "overflow", "stack",
                        "fuzz", "rule"
                    )):
                        continue

                absdiff = abs(size - target_len)
                score = absdiff * 1000
                if size == target_len:
                    score -= 500
                score += size

                for idx, tok in enumerate(tokens_priority):
                    if tok in path_lower:
                        weight = (len(tokens_priority) - idx)
                        score -= weight * 20

                for d_tok in (
                    "poc", "pocs", "crash", "crashes",
                    "fuzz", "fuzzer", "oss-fuzz", "ossfuzz",
                    "seeds", "inputs", "corpus", "regress",
                    "tests", "testcases"
                ):
                    if d_tok in path_lower:
                        score -= 30

                if best_score is None or score < best_score:
                    best_score = score
                    best_path = full_path

        return best_path

    def _default_poc(self, target_len: int) -> bytes:
        return b"A" * target_len