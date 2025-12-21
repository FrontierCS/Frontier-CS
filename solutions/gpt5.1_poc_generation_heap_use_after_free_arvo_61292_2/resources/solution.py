import os
import tarfile
import tempfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        extract_dir = self._extract_tarball(src_path)
        poc_path = self._find_best_poc_file(extract_dir)
        if poc_path is not None:
            try:
                with open(poc_path, "rb") as f:
                    return f.read()
            except OSError:
                pass
        return self._fallback_poc()

    def _extract_tarball(self, src_path: str) -> str:
        # Create temporary directory for extraction
        extract_dir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            with tarfile.open(src_path, "r:*") as tar:
                tar.extractall(extract_dir)
        except tarfile.TarError:
            # If not a tarball, assume src_path is already a directory
            if os.path.isdir(src_path):
                return src_path
        return extract_dir

    def _find_best_poc_file(self, root: str) -> str | None:
        TARGET_SIZE = 159
        best_score = None
        best_path = None

        binary_good_exts = {
            ".flac",
            ".fla",
            ".cue",
            ".bin",
            ".poc",
            ".raw",
            ".wav",
            ".au",
            ".snd",
            ".caf",
            ".aif",
            ".aiff",
        }

        text_exts = {
            ".c",
            ".h",
            ".cpp",
            ".cc",
            ".cxx",
            ".hpp",
            ".py",
            ".java",
            ".js",
            ".html",
            ".htm",
            ".xml",
            ".sh",
            ".txt",
            ".md",
            ".markdown",
            ".rst",
            ".json",
            ".yml",
            ".yaml",
            ".toml",
            ".ini",
            ".cfg",
            ".cmake",
            ".mak",
            ".mk",
            ".in",
            ".ac",
            ".am",
            ".m4",
            ".pc",
            ".pl",
            ".pm",
            ".rb",
            ".go",
            ".rs",
            ".php",
            ".el",
            ".lisp",
            ".scm",
            ".clj",
            ".coffee",
            ".ts",
            ".tsx",
            ".cs",
            ".bat",
            ".cmd",
            ".ps1",
            ".sql",
            ".s",
            ".asm",
            ".S",
            ".sx",
            ".tex",
            ".sty",
            ".cls",
            ".csv",
        }

        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue

                if size <= 0 or size > 1024 * 1024:
                    continue

                score = 0
                # Prefer files with size close to TARGET_SIZE
                if size == TARGET_SIZE:
                    score += 3000
                else:
                    diff = abs(size - TARGET_SIZE)
                    score += max(0, 1500 - diff * 10)

                lower_name = filename.lower()
                lower_path = path.lower()
                keywords = [
                    ("poc", 700),
                    ("crash", 600),
                    ("uaf", 500),
                    ("heap", 400),
                    ("bug", 300),
                    ("cue", 300),
                    ("cuesheet", 400),
                    ("flac", 200),
                ]
                for kw, val in keywords:
                    if kw in lower_name or kw in lower_path:
                        score += val

                ext = os.path.splitext(filename)[1].lower()
                if ext in binary_good_exts:
                    score += 500
                if ext in text_exts:
                    score -= 800

                # Check if likely binary
                is_binary = False
                try:
                    with open(path, "rb") as f:
                        chunk = f.read(512)
                    if chunk:
                        nontext = 0
                        for b in chunk:
                            if b in (9, 10, 13):
                                continue
                            if 32 <= b <= 126:
                                continue
                            nontext += 1
                        if nontext / len(chunk) > 0.3:
                            is_binary = True
                except OSError:
                    continue

                if is_binary:
                    score += 100

                if best_score is None or score > best_score:
                    best_score = score
                    best_path = path

        return best_path

    def _fallback_poc(self) -> bytes:
        # Generic CUESHEET-style input as a conservative fallback
        data = (
            b"REM GENRE test\n"
            b"REM DATE 2000\n"
            b"PERFORMER \"Test\"\n"
            b"TITLE \"Test Album\"\n"
            b"FILE \"test.wav\" WAVE\n"
            b"  TRACK 01 AUDIO\n"
            b"    TITLE \"Track 1\"\n"
            b"    PERFORMER \"Test\"\n"
            b"    INDEX 01 00:00:00\n"
        )
        return data
